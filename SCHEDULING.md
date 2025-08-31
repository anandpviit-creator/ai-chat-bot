# Scheduling Automatic Re-indexing

To keep the chatbot's knowledge base up-to-date with your Confluence instance, you can schedule the indexing script to run automatically at regular intervals (e.g., once per day). A common way to do this on Linux or macOS is by using a **cron job**.

## How It Works

The command will use `docker-compose` to execute the indexing script inside the already running `app` container. The `--reindex` flag is used to ensure that all old data is cleared out before the new data is indexed.

## Prerequisites

-   Your project must be running via `docker-compose up -d`. The `-d` flag runs the containers in detached mode (in the background).
-   You should have a general understanding of how to edit a crontab file on your system.

## Example Cron Job

Here is an example of a cron job that runs the re-indexing script every day at 2:00 AM.

1.  **Open your crontab for editing:**
    ```bash
    crontab -e
    ```

2.  **Add the following line to the file:**
    ```cron
    0 2 * * * /usr/bin/docker-compose -f /path/to/your/project/docker-compose.yml exec app python index_confluence.py --reindex >> /path/to/your/project/cron.log 2>&1
    ```

### Breakdown of the Command:

-   `0 2 * * *`: This is the schedule. It means "at minute 0 of hour 2 on every day-of-month on every month on every day-of-week". In simple terms: **every day at 2:00 AM**.
-   `/usr/bin/docker-compose`: The absolute path to your `docker-compose` executable. This can vary by system; you can find it by running `which docker-compose`.
-   `-f /path/to/your/project/docker-compose.yml`: This specifies the **full, absolute path** to your `docker-compose.yml` file. Cron jobs run in a different environment and need absolute paths to find your project.
-   `exec app`: This tells `docker-compose` to execute a command inside the service named `app` (our Python container).
-   `python index_confluence.py --reindex`: This is the command to run inside the container. We use the `--reindex` flag to perform a full, clean re-indexing.
-   `>> /path/to/your/project/cron.log 2>&1`: This is for logging. It appends all output (both standard output and errors) to a file named `cron.log` in your project directory. This is highly recommended for debugging any issues with the scheduled job.

**Important:** Remember to replace `/path/to/your/project/` with the actual absolute path to this project's directory on your machine. You can get the path by navigating to the project folder in your terminal and running the `pwd` command.
