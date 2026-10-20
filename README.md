# Subscription Management & Automated Billing Platform

A robust, asynchronous backend system built to manage user subscriptions, process automated billing cycles, and execute scheduled tasks seamlessly using **Python**, **SQLAlchemy ORM**, **Alembic**, **Celery**, and **Redis**.

---

## 🚀 Key Features

* **Relational Database Design:** Engineered scalable schemas and models using **SQLAlchemy ORM** for user accounts, subscriptions, invoices, and transaction histories.
* **Database Migrations:** Managed seamless schema evolution and version-controlled database migrations using **Alembic**.
* **Asynchronous Task Processing:** Offloaded heavy computation, scheduled billing jobs, and notification queues to background tasks using **Celery**.
* **In-Memory Message Broker:** Utilized **Redis** for efficient message queuing, caching, and task broker routing.

---

## 🛠️ Tech Stack

* **Language:** Python
* **ORM & Database:** SQLAlchemy, PostgreSQL
* **Database Migrations:** Alembic
* **Task Queue & Broker:** Celery, Redis

---

## ⚙️ Getting Started

### Prerequisites
Make sure you have the following installed on your machine:
* **Python 3.10+**
* **Redis Server**

### 1. Clone the Repository
```bash
git clone [https://github.com/Sivarama27/Subscription-Management-and-Automated-Billing-Platform-.git](https://github.com/Sivarama27/Subscription-Management-and-Automated-Billing-Platform-.git)
cd billing-platform

2. Set Up Virtual Environment
Bash
# On Windows
python -m venv venv
.\venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate

3. Install Dependencies
Bash
pip install -r requirements.txt
4. Run Database Migrations
Bash
alembic upgrade head
5. Start Redis & Celery Worker
Bash
# Start Redis
redis-server

# Start Celery Worker
celery -A main.celery worker --loglevel=info
📂 Project Structure
Plaintext
billing-platform/
│-- alembic/              # Database migration scripts
│-- models/               # SQLAlchemy ORM models
│-- tasks/                # Celery asynchronous background tasks
│-- alembic.ini           # Alembic configuration
│-- requirements.txt      # Project dependencies
└── README.md             # Project documentation
