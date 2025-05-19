# urlsdigest

**Crawl a list of URLs and generate a Markdown digest of their contents.**

`urlsdigest` is a command-line tool built on top of `crawl4ai` that extracts readable Markdown content from one or more web pages and saves it to a single `.md` file. It supports real-time monitoring, concurrency control, and headless browser automation.

---

## 🚀 Features

- ✅ Extracts Markdown content from URLs
- 🧠 Smart concurrency with memory-adaptive dispatching
- 👁️ Optional real-time terminal monitor
- 📂 Supports URLs from a file or CLI args
- 💾 Saves output as a clean, structured Markdown digest

---

## 📦 Installation with [`uv`](https://github.com/astral-sh/uv)

### 1. Install [uv](https://github.com/astral-sh/uv) (if you haven't)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
````

or use `brew install astral-sh/uv/uv` on macOS.

---

### 2. Clone and install the tool

```bash
git clone https://github.com/asuworks/urlsdigest.git
cd urlsdigest

uv venv # create virtual env
# or
uv sync # sync virtual env

uv pip install --editable . # install in virtual env
uv pip install --editable .[dev] # install in virtual env with dev dependencies
uv pip install --editable . --system # install globally
```

Make sure your `pyproject.toml` includes:

```toml
[project.scripts]
urlsdigest = "urls_digest:cli"
```

This exposes the `urlsdigest` command globally.

---

## 🧪 Usage

```bash
urlsdigest [OPTIONS] [URLS]...
```

### Examples

#### Crawl a few URLs directly:

```bash
urlsdigest https://example.com https://openai.com -o digest.md
```

#### Use a file with URLs:

```bash
urlsdigest --urls-file urls.txt -o summary.md
```

> Lines starting with `#` in the file will be ignored.

---

## 🛠 Options

| Option                       | Description                                                        |
| ---------------------------- | ------------------------------------------------------------------ |
| `-o, --output`               | Output file for the Markdown digest (default: `crawled_digest.md`) |
| `--headless / --no-headless` | Run the browser in headless mode (default: `--headless`)           |
| `--verbose-crawl`            | Enable verbose crawl logs                                          |
| `--monitor / --no-monitor`   | Enable or disable real-time monitor UI                             |
| `--max-concurrent`           | Maximum number of concurrent browser sessions (default: `5`)       |
| `--urls-file`                | Path to a file with one URL per line                               |

---

## 📝 Output Format

The output file contains:

* A YAML-style frontmatter summary (date, stats)
* Structured sections for each URL
* Error messages for failed crawls

---

## ✅ Requirements

* Python `>=3.12.7`
* [`uv`](https://github.com/astral-sh/uv)
* [`crawl4ai`](https://pypi.org/project/crawl4ai/)

---