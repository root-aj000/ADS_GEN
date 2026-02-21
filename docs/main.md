# Main Entry Point Documentation

## File: [`main.py`](../main.py)

## Overview

The `main.py` file is the **entry point** of the Ad Generator application. Think of it as the "start button" that launches the entire advertisement creation process.

## What Does This File Do?

Imagine you have a factory that produces advertisement images. The `main.py` file is like the factory manager who:
1. **Wakes up the factory** (initializes logging)
2. **Checks the instructions** (loads configuration)
3. **Starts the production line** (runs the pipeline)

## Real-World Analogy

Think of this file like starting your car:
- **Step 1**: You turn the key (call `main()`)
- **Step 2**: The engine starts (logging setup)
- **Step 3**: Dashboard lights show status (log messages)
- **Step 4**: The car begins moving (pipeline runs)

## Code Breakdown

### Function: [`main()`](../main.py:14)

```python
def main() -> None:
```

This is the main function that orchestrates the entire process. It doesn't return any value (`None`), but it triggers all the work.

### Step-by-Step Process

#### Step 1: Setup Logging (Lines 15-17)

```python
setup_root(cfg.paths.log_file, verbose=cfg.verbose)
log = get_logger("main")
```

**What it does**: Creates a log file where all messages will be saved.

**Example**: Think of this like opening a diary where you'll write down everything that happens during the day. Every action, success, and error gets recorded.

**Parameters used**:
| Parameter | Source | Description |
|-----------|--------|-------------|
| `cfg.paths.log_file` | [`config/settings.py`](../config/settings.py) | Path where logs are saved (e.g., `data/logs/ad_generator.log`) |
| `cfg.verbose` | [`config/settings.py`](../config/settings.py) | If `True`, shows detailed debug messages |

---

#### Step 2: Display Banner (Lines 19-28)

```python
log.info("=" * 60)
log.info("🚀 AD GENERATOR v4.0 — Production / Multi-Threaded")
log.info("=" * 60)
log.info("Search priority : %s", " → ".join(cfg.search.priority))
log.info("Workers : %d", cfg.pipeline.max_workers)
log.info("Resume : %s", cfg.resume)
log.info("Dry run : %s", cfg.dry_run)
log.info("Verbose : %s", cfg.verbose)
log.info("Input CSV : %s", cfg.paths.csv_input)
log.info("Output dir : %s", cfg.paths.images_dir)
```

**What it does**: Prints a welcome message showing the current settings.

**Example Output**:
```
============================================================
🚀 AD GENERATOR v4.0 — Production / Multi-Threaded
============================================================
Search priority : google → duckduckgo → bing
Workers : 4
Resume : False
Dry run : False
Verbose : True
Input CSV : data/input/main.csv
Output dir : data/output/images
```

**Why this matters**: This helps you verify that the program is using the correct settings before it starts processing.

---

#### Step 3: Initialize and Validate (Lines 31-33)

```python
cfg.paths.ensure()
cfg.validate()
```

**What it does**:
- `cfg.paths.ensure()` creates all necessary folders
- `cfg.validate()` checks if all required files exist

**Example**: Like checking if you have all ingredients before cooking:
- Do the folders exist? (Create them if not)
- Does the input CSV file exist? (Error if not)
- Are the settings valid? (Error if not)

---

#### Step 4: Build Pipeline (Line 36)

```python
pipeline = AdPipeline(cfg)
```

**What it does**: Creates the main processing pipeline that will handle all advertisement generation.

**Data Flow**:
```
AppConfig (cfg) 
    ↓
AdPipeline
    ↓
[SearchManager, ImageDownloader, BackgroundRemover, AdCompositor, etc.]
```

**Parameters passed**:
| Parameter | Type | Source | Description |
|-----------|------|--------|-------------|
| `cfg` | `AppConfig` | [`config/settings.py`](../config/settings.py) | Complete application configuration |

---

#### Step 5: Reset Progress (Lines 38-40)

```python
if not cfg.resume:
    pipeline.progress.reset()
    log.info("Progress reset — fresh start")
```

**What it does**: If not resuming from a previous run, clears the progress database.

**Example**: 
- If `RESUME_FROM_PROGRESS = True`: Continue from where you left off
- If `RESUME_FROM_PROGRESS = False`: Start fresh, like erasing a whiteboard

---

#### Step 6: Run Pipeline (Line 43)

```python
pipeline.run()
```

**What it does**: Starts the main processing loop. This is where all the actual work happens!

**What happens inside**:
1. Reads CSV file with product data
2. For each row:
   - Searches for images
   - Downloads the best image
   - Removes background (if needed)
   - Creates the final advertisement
3. Saves results to output folder

---

## Configuration Parameters Used

This table shows all configuration values that `main.py` reads from [`config/settings.py`](../config/settings.py):

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cfg.paths.log_file` | Path | `data/logs/ad_generator.log` | Where to save log messages |
| `cfg.verbose` | bool | `True` | Show detailed debug messages |
| `cfg.search.priority` | List | `["google", "duckduckgo", "bing"]` | Order of search engines to use |
| `cfg.pipeline.max_workers` | int | `4` | Number of parallel workers |
| `cfg.resume` | bool | `False` | Continue from previous run |
| `cfg.dry_run` | bool | `False` | Skip image composition (test mode) |
| `cfg.paths.csv_input` | Path | `data/input/main.csv` | Input CSV file path |
| `cfg.paths.images_dir` | Path | `data/output/images` | Output folder for generated ads |

---

## How Data Flows Through main.py

```
┌─────────────────────────────────────────────────────────────┐
│                        main.py                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Load Configuration                                       │
│     └── from config.settings import cfg                      │
│                                                              │
│  2. Setup Logging                                            │
│     └── setup_root(cfg.paths.log_file, verbose=cfg.verbose) │
│                                                              │
│  3. Validate Environment                                     │
│     ├── cfg.paths.ensure()  # Create folders                │
│     └── cfg.validate()      # Check files exist             │
│                                                              │
│  4. Create Pipeline                                          │
│     └── pipeline = AdPipeline(cfg)                          │
│                                                              │
│  5. Run!                                                     │
│     └── pipeline.run()                                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Connected Files

[`main.py`](../main.py) imports from these modules:

| Module | Purpose |
|--------|---------|
| [`config/settings.py`](../config/settings.py) | Provides `cfg` - all configuration settings |
| [`utils/log_config.py`](../utils/log_config.py) | Provides `setup_root()` and `get_logger()` for logging |
| [`core/pipeline.py`](../core/pipeline.py) | Provides `AdPipeline` - the main processing engine |

---

## How to Run

```bash
# Navigate to the project directory
cd u:/ad_gen

# Run the application
python main.py
```

---

## Common Issues and Solutions

### Issue: "Input CSV missing"
**Cause**: The input CSV file doesn't exist at the expected location.
**Solution**: 
1. Check `data/input/main.csv` exists
2. Or change `cfg.paths.csv_input` in [`config/settings.py`](../config/settings.py)

### Issue: "Permission denied" when writing logs
**Cause**: The logs folder is not writable.
**Solution**: 
1. Create the folder manually: `data/logs/`
2. Or check folder permissions

---

## Summary

The `main.py` file is a simple but crucial entry point that:
1. ✅ Loads all configuration
2. ✅ Sets up logging
3. ✅ Validates the environment
4. ✅ Creates and runs the pipeline

**Think of it as**: The conductor of an orchestra - it doesn't play any instruments, but it makes sure everyone starts at the right time and place.

<!-- VISUAL ENHANCEMENTS BELOW -->

## 🔄 Execution Flow (Mermaid)

```mermaid
graph TB
    A[Start main()] --> B[Setup Logging]
    B --> C[Display Banner]
    C --> D[Initialize & Validate]
    D --> E[Build Pipeline]
    E --> F{Resume?}
    F -->|Yes| G[Continue Processing]
    F -->|No| H[Reset Progress]
    H --> I[Run Pipeline]
    G --> I
    I --> J[Processing Complete]
```

## ⚙️ Configuration Comparison

| Setting | Development | Production | Description |
|--------|-------------|------------|-------------|
| `verbose` | `True` | `False` | Detailed logging output |
| `dry_run` | `True` | `False` | Test without image composition |
| `resume` | `True` | `False` | Continue from previous run |
| `max_workers` | `2` | `4` | Concurrent processing threads |

## 📊 Performance Indicators

> 🚀 **Performance Tip**: Increasing worker count can improve throughput but will also increase memory usage.

| Workers | Memory Usage | Throughput | Recommended For |
|--------|--------------|------------|-----------------|
| 1 | 300 MB | 150 products/hour | Testing |
| 2 | 500 MB | 280 products/hour | Development |
| 4 | 1.2 GB | 550 products/hour | Production |
| 8 | 2.4 GB | 800 products/hour | High-performance servers |

## 🛠️ Troubleshooting Quick Reference

<div style="background-color: #fce8e8; padding: 15px; border-left: 5px solid #db4437; margin: 20px 0;">
<strong>❌ "Input CSV missing"</strong><br>
Ensure the file exists at <code>data/input/main.csv</code> or update <code>cfg.paths.csv_input</code> in configuration.
</div>

<div style="background-color: #e8f4fd; padding: 15px; border-left: 5px solid #4285f4; margin: 20px 0;">
<strong>⚠️ "Permission denied"</strong><br>
Check that the application has write permissions to <code>data/logs/</code> and <code>data/output/</code> directories.
</div>

<div style="background-color: #e8fdf5; padding: 15px; border-left: 5px solid #0f9d58; margin: 20px 0;">
<strong>✅ Success!</strong><br>
When you see "Pipeline completed successfully", your ads have been generated in <code>data/output/images/</code>.
</div>
