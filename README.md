<!-- TABLE OF CONTENTS -->
<details>
  <summary>📚 Table of Contents</summary>
  <ol>
    <li>
      <a href="#-about-the-project">⭐ About The Project</a>
    </li>
    <li><a href="#-feature">📋 Feature</a></li>
    <li><a href="#-tech-stack">⚡ Tech Stack</a></li>
    <li>
      <a href="#-getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
        <li><a href="#setup-environtment">Setup Environment</a></li>
        <li><a href="#run-the-project">Run The Project</a></li>
      </ul>
    </li>
    <li><a href="#-team">Team</a></li>
  </ol>
</details>

<!-- ABOUT THE PROJECT -->

## ⭐ About The Project

Es Teler

## 📋 Feature

- [ ] 📅 Reservation
  - [ ] Advanced Doctor Search : Patients can filter doctors by Polyclinic, Day, and Time.
- [ ] 📝 Data Management for Admin
  - [ ] Doctor Management

## ⚡ Tech Stack

- [![Flask][Flask.py]][Flask-url]
- [![Javascript][Javascript]][AzureSQL-url]
- [![TailwindCSS][Tailwind]][Tailwind-url]

<!-- GETTING STARTED -->

## 🚀 Getting Started

Berikut ini adalah _prerequisites_ dan _installation_ jika ingin menjalankan proyek secara lokal.
Ikuti instruksi dibawah untuk mendapatkan _local copy_ dari proyek ini.

### Prerequisites

Before you begin, ensure you have met the following requirements:

1. Operating System
   Windows (Recommended for SQL Server compatibility), macOS, or Linux.

2. Software & Tools
   - Python 3.10+: Make sure Python is installed and added to your system PATH.
   - Node.js & npm: Required to compile Tailwind CSS locally.
   - Git: To clone the repository.
   - Microsoft SQL Server: You need a running instance of SQL Server (Express or Developer edition is free for local use).

   - ODBC Driver 18 for SQL Server:
     This is mandatory for the application to connect to the database.
     [Download for Windows, macOS, and Linux here.](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server?view=sql-server-ver17)

   - Database Management Tool (Optional but recommended):
     - SSMS (SQL Server Management Studio) or Azure Data Studio to visualize and manage your tables.

3. Knowledge
   - Basic understanding of how to use the Command Line or Terminal.

### Installation

1. Clone repository
   ```sh
   git clone https://github.com/yudhasw/Telkomedika-Online-Reservation.git
   ```
2. Buat Virtual Environment Python
   ```sh
   python -m venv .venv
   ```
   Aktifkan Environment
   ```sh
   .venv\Scripts\activate
   ```
3. Install Dependencies Python
   ```sh
   pip install -r requirements.txt
   ```
4. Install Dependencies NPM
   ```sh
   npm install
   ```

### Setup Environment

1. Make .env File
2. Copy this Code and fill it with your own data.
   ```sh
   SERVER_NAME=YourServerName
   DATABASE_NAME=YourDatabaseName
   DB_USERNAME=YourDatabaseUsername
   DB_PASSWORD=password_rahasia
   SECRET_KEY=random_secret_key
   MAIL_USERNAME=email@gmail.com
   MAIL_PASSWORD=app_password_google
   ```

### Run the Project

```sh
npm run dev
```

## 👨🏻‍💻 Team

- Devo Gassan Savero
- Arya Wijaya 103012330330
- Arif Rahmatiana 103012300446
- Syauqi Nurfikri Rahman 103012300299
- Dhafin Ghiffary 103012300348
- Yudha Setiawan Wicaksono 103012300480
- Muhammad Nazriel Ihram 103012300269

<br />
<a href="https://github.com/yudhasw/Telkomedika-Online-Reservation/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=yudhasw/Telkomedika-Online-Reservation" alt="contrib.rocks image" />
</a>
