## Setup

1. Install Python 2.7
2. [Enable drive API](https://developers.google.com/drive/v3/web/quickstart/python#step_1_turn_on_the_api_name)
2. [Install library](https://developers.google.com/drive/v3/web/quickstart/python#step_2_install_the_google_client_library)
3. Clone repo, `git clone https://github.com/joelgarboden/gdrive_ftp.git`
4. Edit [config.json](https://raw.githubusercontent.com/joelgarboden/gdrive_ftp/master/config.json), taking heed to `drive.client_secrets`, `drive.credentials_cache`, `ftp.local_cache`, and `users`
5. Authorize ftp server, `python main.py --noauth_local_webserver`, follow prompts, then enter to exit
6. Launch GDrive to FTP server with `python main.py`