# Spendsy

**Version:** v5.3.0  
**Type:** Final Year Project (FYP)

A comprehensive Personal Finance PWA tailored for the Indian market, featuring AI-driven tax audits and bank statement parsing.

## 🚀 Features

- **🇮🇳 Indian Tax Engine:** Calculates liability under Old & New Regimes (80C, 80D, HRA, etc.).
- **🤖 AI Advisor:** Gemini-powered insights for monthly spending and tax planning.
- **📄 Statement Parsing:** OCR & PDF support for SBI, HDFC, ICICI, Axis, and Citi statements.
- **💰 Wealth Tracking:** Real-time Net Worth calculation (Assets - Liabilities).
- **📱 Offline Ready:** Built as a PWA with Firebase persistence.

---

## 🛠️ Developer Workflow (Git commands)

### 📋 Branch Naming Rules
*Please use these prefixes when creating branches:*
* **New Features:** `feature/your-feature-name` (e.g., `feature/login-page`)
* **Bug Fixes:** `fix/issue-name` (e.g., `fix/login-error`)

---

### For Repo Creator (Tanu)

#### A. Initial Setup (One-time only)
- 1. Clone your repository <br>
```git clone https://github.com/TanushreeMohanty/Smart-Spend-FYP.git```

- 2. Enter the directory <br>
```cd Smart-Spend-FYP```

#### B. Reviewing & Merging Code 
(Run this when a team member has finished a task.)

- 1. Get the latest updates from GitHub <br>
```git fetch origin```

- 2. Switch to the team member's branch to test their code <br>
```git checkout team-member-branch-name```

- 3. ... Test the app to ensure it works ... <br>
```npm run dev```

- 4. If it works, switch back to main <br>
```git checkout main```

- 5. Merge their work into the main code <br>
```git merge team-member-branch-name```

- 6. Push the updated main code to GitHub <br>
```git push origin main```

### For team members (Rohin & Shubham)

#### A. Initial Setup (One-time only)
- 1. Clone your repository <br>
```git clone https://github.com/TanushreeMohanty/Smart-Spend-FYP.git```

- 2. Enter the directory <br>
```cd Smart-Spend-FYP```

#### B. Daily Work Cycle
- 1. VITAL: Switch to main and get the latest code <br>
```git checkout main``` <br>
```git pull origin main```

- 2. Create a new branch for your task (Replace 'feature/login-page' with your actual task name) <br>
```git checkout -b feature/login-page```

- 3. ... Write your code and make changes ...

- 4. Save your changes locally <br>
```git add .``` <br>
```git commit -m "Description of what you added"``` 

- 5. Upload your branch to GitHub <br>
```git push origin feature/login-page```

#### C. Finalizing (Pull Request)
- 1. Go to the GitHub Repository.

- 2. You will see a banner saying "Compare & pull request".

- 3. Click it, write a short title, and click Create Pull Request to notify the Owner and Do not click on any merge button.


## Codes to run

For backend:
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

### Work to do
- AI Consultant feature in Audit page
- Watchdog feature in Stats page

- host on render





