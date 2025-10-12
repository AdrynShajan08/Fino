# Fino - Personal Finance App

A web app to help manage personal finances (track expenses and record investments).

## ✨ Features

- 📊 **Dashboard** - Visual overview of expenses and investments
- 💰 **Expense Tracking** - Record and categorize expenses
- 💹 **Investment Tracking** - Monitor investment portfolio
- 🔐 **User Authentication** - Secure login system
- ✅ **Logging**: Error tracking

## 🛠️ Installation

```bash
   git clone <repository-url>
   cd fino
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env # Edit .env and set your SECRET_KEY
   python -c "from services.db_handler import initialize_database; initialize_database('data.db')" #database initialization
   python app.py
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

- `FLASK_ENV`: Set to `development` or `production`
- `SECRET_KEY`: Change this to a random secret key in production
- `DATABASE_PATH`: Path to SQLite database file

## 📝 API Endpoints

### Authentication

- `GET/POST /register` - User registration
- `GET/POST /login` - User login
- `GET /logout` - User logout

### Expenses

- `POST /add_expense` - Add new expense
- `GET /get_expenses` - Get expense summary
- `GET /get_expenses_full` - Get all expenses (with filters)
- `POST /update_expense/<id>` - Update expense
- `DELETE /delete_expense/<id>` - Delete expense
- `GET /get_summary` - Get category summary
- `GET /get_monthly_trend` - Get monthly trend

### Investments

- `POST /add_investment` - Add new investment
- `GET /get_investments` - Get investment summary
- `GET /get_investments_full` - Get all investments (with filters)
- `POST /update_investment/<id>` - Update investment
- `DELETE /delete_investment/<id>` - Delete investment
- `GET /get_investment_trend` - Get investment trend

### Dashboard

- `GET /` - Main dashboard
- `GET /profile` - User profile

## 👤 Author

Edryn Eazhakadan
