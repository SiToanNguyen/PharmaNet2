# PharmaNet2

PharmaNet2 is a personal project that I work on independently. The goal is to provide tools for pharmacies, helping them operate more efficiently and save time. This is a remake of my bachelor’s project. In this version, I've switched from Flask and SQLite (used in the original version) to Django and PostgreSQL to improve performance and scalability. The web application is deployed on Amazon Web Services (AWS).

## Features

- Manage products, manufacturers, and categories.
- Manage purchase and sale transactions, and track finances.
- Manage inventory, track products coming in and out, and monitor expiry dates.
- Generate financial and inventory reports.
- Keep activity logs of system use, including user actions and timestamps.

## Accessing the Demo Website on AWS

To try out the live demo hosted on AWS:

1. Start the server by visiting the proxy page:  
   [http://pharmanet-proxy-page.s3-website.eu-north-1.amazonaws.com/](http://pharmanet-proxy-page.s3-website.eu-north-1.amazonaws.com/)

2. Wait for the server to boot up. This may take up to 2 minutes.

3. When the server is ready, its URL will be displayed on the page.

## Installation

1. Clone the repo:
   ```bash
   git clone https://github.com/SiToanNguyen/PharmaNet2.git
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the project with:

```bash
python manage.py runserver
```

## Contributing

This project is for viewing only. If you'd like to make changes, feel free to clone the repository and modify it as you wish.

## License

This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License.  
You are free to use, share, and modify the code, but **not for commercial purposes**.  
See the [LICENSE](LICENSE) file for more details.
