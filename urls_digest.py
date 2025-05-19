import asyncio
import os
from datetime import datetime
from typing import List, Tuple # click.Path needs Tuple for path type
import click # CLI library

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode,
    CrawlResult,
    CrawlerMonitor,
    # DisplayMode, # Commented out due to previous error with user's version
    MemoryAdaptiveDispatcher
)

# Global variable to store URLs from file if used, to combine with CLI args
_urls_from_file_global: List[str] = []

def read_urls_from_file_callback(ctx, param, value):
    """Callback for click to read URLs from a file."""
    global _urls_from_file_global
    if value:
        try:
            with open(value, 'r', encoding='utf-8') as f:
                _urls_from_file_global = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            if not _urls_from_file_global:
                click.echo(click.style(f"Warning: URL file '{value}' is empty or only contains comments.", fg="yellow"))
        except FileNotFoundError:
            raise click.BadParameter(f"File not found: {value}")
        except Exception as e:
            raise click.BadParameter(f"Could not read file {value}: {e}")
    return value


async def create_markdown_digest(
    urls_to_crawl: List[str],
    output_file: str,
    headless: bool,
    verbose_crawl: bool,
    enable_monitor: bool,
    max_concurrent_sessions: int
):
    """
    Crawls a list of URLs, extracts their markdown content,
    and concatenates them into a single markdown digest file,
    with optional real-time monitoring.
    """
    if not urls_to_crawl:
        click.echo(click.style("No URLs provided to crawl.", fg="red"))
        return

    click.echo(f"Starting crawl for {len(urls_to_crawl)} URLs...")
    if enable_monitor:
        click.echo("Monitoring enabled.")

    browser_config = BrowserConfig(
        headless=headless,
        verbose=verbose_crawl
    )

    crawler_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        verbose=verbose_crawl,
        word_count_threshold=10 # Keep this low to get most content from docs
    )

    all_markdown_parts = []
    successful_crawls = 0
    failed_crawls = 0

    monitor = None
    dispatcher = None

    if enable_monitor:
        monitor = CrawlerMonitor(
            urls_total=len(urls_to_crawl),
            refresh_rate=0.5,
            enable_ui=True # Using enable_ui based on previous error
        )
        dispatcher = MemoryAdaptiveDispatcher(
            max_session_permit=max_concurrent_sessions,
            monitor=monitor,
            memory_threshold_percent=90.0, # Default
            check_interval=1.0             # Default
        )
        monitor.start()
    else:
        # Still use a dispatcher for concurrency, just without the UI monitor
        dispatcher = MemoryAdaptiveDispatcher(
            max_session_permit=max_concurrent_sessions,
            memory_threshold_percent=90.0,
            check_interval=1.0
        )

    crawl_results_list: List[CrawlResult] = []
    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            # arun_many returns results in the order of input URLs if stream=False (default)
            crawl_results_list = await crawler.arun_many(
                urls=urls_to_crawl,
                config=crawler_config,
                dispatcher=dispatcher
            )
    finally:
        if monitor:
            monitor.stop()
            await asyncio.sleep(0.1) # Allow monitor to clear up display

    if enable_monitor: # Print this after monitor has stopped
        click.echo(f"\nProcessing {len(crawl_results_list)} results...\n")

    for result in crawl_results_list: # Process in the original order
        if result.success:
            successful_crawls += 1
            if not enable_monitor:
                click.echo(click.style(f"[SUCCESS] Fetched: {result.url}", fg="green"))

            all_markdown_parts.append(f"# Content from: {result.url}\n\n")
            if result.markdown and hasattr(result.markdown, 'raw_markdown'):
                all_markdown_parts.append(result.markdown.raw_markdown)
            elif result.markdown and isinstance(result.markdown, str):
                all_markdown_parts.append(result.markdown)
            else:
                if not enable_monitor:
                     click.echo(click.style(f"  [WARNING] No markdown content found for: {result.url}", fg="yellow"))
                all_markdown_parts.append(f"*No markdown content found for this URL: {result.url}*")
            all_markdown_parts.append("\n\n---\n\n")
        else:
            failed_crawls += 1
            if not enable_monitor:
                click.echo(click.style(f"[FAILED]  URL: {result.url}", fg="red"))
                click.echo(click.style(f"  Error: {result.error_message}", fg="red"))
            all_markdown_parts.append(f"# Failed to fetch: {result.url}\n\n")
            all_markdown_parts.append(f"Error: `{result.error_message}`\n\n")
            all_markdown_parts.append("\n\n---\n\n")

    digest_header = f"""---
title: URL Content Digest
date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
urls_processed: {len(urls_to_crawl)}
successful_crawls: {successful_crawls}
failed_crawls: {failed_crawls}
---

"""
    final_markdown_content = digest_header + "\n".join(all_markdown_parts)

    try:
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            click.echo(f"Created directory: {output_dir}")

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(final_markdown_content)
        click.echo(click.style(f"\nSuccessfully created digest: {os.path.abspath(output_file)}", fg="green"))
        click.echo(f"Total URLs processed: {len(urls_to_crawl)}")
        click.echo(f"Successful crawls: {successful_crawls}")
        click.echo(f"Failed crawls: {failed_crawls}")
    except IOError as e:
        click.echo(click.style(f"Error writing to file {output_file}: {e}", fg="red"))
    except Exception as e:
        click.echo(click.style(f"An unexpected error occurred: {e}", fg="red"))


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.argument('urls_args', nargs=-1, type=str, metavar='[URLS]...')
@click.option(
    '--urls-file',
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to a file containing URLs to crawl, one URL per line (lines starting with # are ignored).",
    callback=read_urls_from_file_callback,
    is_eager=True
)
@click.option(
    '-o', '--output',
    default="crawled_digest.md",
    type=click.Path(dir_okay=False, writable=True, resolve_path=True),
    show_default=True,
    help="Output file for the markdown digest."
)
@click.option(
    '--headless/--no-headless',
    default=True,
    show_default=True,
    help="Run the browser in headless mode."
)
@click.option(
    '--verbose-crawl',
    is_flag=True,
    default=False,
    help="Enable verbose logging from crawl4ai library."
)
@click.option(
    '--monitor/--no-monitor',
    default=True,
    show_default=True,
    help="Enable real-time crawling monitor in the terminal."
)
@click.option(
    '--max-concurrent',
    default=5,
    type=click.IntRange(min=1),
    show_default=True,
    help="Maximum number of concurrent browser sessions."
)
def cli(urls_args: Tuple[str], urls_file: str, output: str, headless: bool, verbose_crawl: bool, monitor: bool, max_concurrent: int):
    """
    Crawls a list of URLs and concatenates their markdown content into a single digest file.

    URLs can be provided directly as arguments after all options, or via a file
    specified with --urls-file. If both are provided, URLs from the file are
    processed first, followed by direct arguments.

    The content from each URL will appear in the digest in the order the URLs are provided.
    Lines in the URL file starting with '#' are treated as comments and ignored.
    """
    # _urls_from_file_global is populated by the callback
    combined_urls = _urls_from_file_global + list(urls_args)

    seen_urls = set()
    final_urls_to_crawl = []
    for url in combined_urls:
        if url and url not in seen_urls: # Ensure URL is not empty
            final_urls_to_crawl.append(url)
            seen_urls.add(url)
    
    if not final_urls_to_crawl:
        click.echo(click.style("No URLs specified. Provide URLs as arguments or via --urls-file.", fg="red"))
        ctx = click.get_current_context()
        click.echo(ctx.get_help())
        ctx.exit(1)

    # Manage asyncio event loop
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(create_markdown_digest(
            urls_to_crawl=final_urls_to_crawl,
            output_file=output,
            headless=headless,
            verbose_crawl=verbose_crawl,
            enable_monitor=monitor,
            max_concurrent_sessions=max_concurrent
        ))
    except KeyboardInterrupt:
        click.echo(click.style("\nCrawl interrupted by user.", fg="yellow"))
    finally:
        # Close the loop only if it was created by this function and is not running
        if not getattr(loop, 'is_running_custom', False) and not loop.is_running():
            # Gracefully shut down any remaining tasks
            tasks = asyncio.all_tasks(loop)
            if tasks:
                for task in tasks:
                    task.cancel()
                try:
                    loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
                except asyncio.CancelledError:
                    pass # Expected if tasks are cancelled
            loop.close()


if __name__ == "__main__":
    cli()