# 📦 SQLite to HuggingFace Dataset

<p align="center">
  <img src="logo.png" alt="SQLite to HuggingFace Logo" width="300px">
</p>

A lightweight, memory-efficient utility to convert SQLite tables or custom SQL queries into HuggingFace Datasets and push them directly to the Hub.

## ✨ Features

- 🚀 **Memory Efficient**: Uses Python generators and `datasets.Dataset.from_generator` to handle large databases without loading everything into RAM.
- 🔍 **Schema Preview**: Automatically infers and prints your data schema before uploading.
- 🛠️ **Custom Queries**: Use any SQL `SELECT` query to filter or join data before export.
- 🔒 **Private Datasets**: Easily create private or public repositories on the Hub.
- 🧪 **Dry Run Mode**: Preview the first few rows and schema without touching the HuggingFace Hub.
- ⚡ **Batch Processing**: Configurable batch sizes for SQLite fetching.

## 🚀 Getting Started

### 1. Install Dependencies

```bash
pip install datasets huggingface_hub
```

### 2. Authenticate with HuggingFace

Log in once to cache your token (stored in `~/.cache/huggingface`):

```bash
hf auth login
```

## 📖 Usage

### Basic Upload

Upload an entire table to a new or existing repository:

```bash
python sqlite_to_hf.py mydata.db users my-username/my-dataset
```

### Private Dataset

Create the repository as private:

```bash
python sqlite_to_hf.py mydata.db users my-username/my-dataset --private
```

### Custom SQL Query

Filter or join tables using the `--query` flag:

```bash
python sqlite_to_hf.py mydata.db users my-username/my-dataset \
  --query "SELECT id, name, email FROM users WHERE active=1"
```

### Dry Run (Preview)

Inspect the schema and the first few rows without uploading:

```bash
python sqlite_to_hf.py mydata.db users my-username/my-dataset --dry-run
```

## ⚙️ Configuration Options

| Argument | Description | Default |
| :--- | :--- | :--- |
| `db_path` | Path to the SQLite database file | (Required) |
| `table` | Table name to export (used for logging/defaults) | (Required) |
| `repo_id` | HuggingFace repo ID (e.g., `user/dataset`) | (Required) |
| `--split` | Dataset split name | `train` |
| `--private` | Create the dataset as private | `False` |
| `--token` | HuggingFace API token (overrides cached login) | `None` |
| `--query` | Custom SQL query to run | `None` |
| `--batch-size` | Rows per batch for SQLite fetching | `10,000` |
| `--dry-run` | Fetch and preview without uploading | `False` |

---

## 📜 License

This project is licensed under the **GNU General Public License v3.0 (GPL-3.0)**. See the [LICENSE](LICENSE) file for details.

## 🌱 Our Philosophy: Pay It Forward

We believe in the power of open-source and the strength of the community. This tool is free to use, modify, and distribute. If you find it helpful, we encourage you to **pay it forward**:

- **Share your knowledge**: Help someone else solve a problem.
- **Contribute**: Submit a PR, improve documentation, or report a bug.
- **Build together**: Use this as a foundation for even better tools.

<p align="center">
  Made with ❤️ for the Open Source Community
</p>
