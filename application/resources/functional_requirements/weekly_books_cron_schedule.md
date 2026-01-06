# Weekly Books Pipeline Schedule

Cron: 0 9 * * 3  # Every Wednesday at 09:00 UTC
Target workflow: books_data_extraction (version 1)
Trigger behavior: run full extraction and then pass output to books_analysis_and_reporting
