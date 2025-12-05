# Weekly Plan Sync

Syncs your weekly planning markdown files to Google Calendar, Google Keep, and Google Tasks.

## What It Does

- **Meals** → Google Calendar ("Food" calendar) at specific times:
  - Breakfast: 7:30 AM
  - Lunch: 11:30 AM  
  - Dinner: 6:30 PM
  - Snacks: 3:00 PM

- **Grocery Shopping** → Google Keep ("Shopping List")

- **Things to Do** → Google Tasks ("Stuff to do" list)

## Setup (One-Time)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get Google API Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable these APIs:
   - Google Calendar API
   - Google Tasks API
4. Go to "Credentials" → "Create Credentials" → "OAuth client ID"
5. Choose "Desktop app" as application type
6. Download the JSON file and save it (e.g., `credentials.json`)

### 3. Create "Food" Calendar

In Google Calendar, create a new calendar called "Food" (if you don't have one already).

### 4. Get Google Keep Credentials

Google Keep doesn't have an official API, so you'll need an **App Password**:

1. Go to [Google Account App Passwords](https://myaccount.google.com/apppasswords)
2. Create a new app password (name it "Weekly Planner" or similar)
3. Copy the 16-character password
4. Use this instead of your regular password

**Note:** You'll need 2-factor authentication enabled to use app passwords.

## Usage

### Basic Command

```bash
python sync-week.py thisweek.md \
  --google-creds credentials.json \
  --keep-user your.email@gmail.com \
  --keep-pass your-app-password
```

### First Run

The first time you run it, a browser will open asking you to authorize access to Google Calendar and Tasks. After authorization, a `token.pickle` file is created so you won't need to do this again.

### Example Weekly File Format

```markdown
Monday:
  Breakfast (7:30am): Oatmeal with berries
  Lunch (11:30am): Salad with chicken
  Dinner (6:30pm): Spaghetti with homemade meatballs
  Snacks (3pm): Apple and almonds
  GroceryShopping:
    - Oats
    - Berries
    - Chicken breast
    - Pasta
    - Ground beef
  Things:
    - Organize office
    - Call dentist
    - Review Q4 budget

Tuesday:
  Breakfast (7:30am): 
  Lunch (11:30am): Leftovers
  Dinner (6:30pm): Mini pizzas
  Snacks (3pm):
  Things:
    - Organize office
    - Go to False Idol
```

## Tips

### Creating a Helper Script

Create a file called `run-sync.sh`:

```bash
#!/bin/bash
python sync-week.py thisweek.md \
  --google-creds credentials.json \
  --keep-user your.email@gmail.com \
  --keep-pass "your-app-password"
```

Make it executable:
```bash
chmod +x run-sync.sh
```

Then you can just run: `./run-sync.sh`

### Automating with Git

You could set up a GitHub Action or git hook to run this automatically when you commit your weekly file. Let me know if you want help with that!

### Week Detection

The script automatically uses the upcoming Monday as the start of your week. If you run it on a Monday, it uses that Monday.

## Troubleshooting

**"Food calendar not found"**
- Make sure you have a calendar named exactly "Food" in Google Calendar

**Google Keep login fails**
- Use an App Password, not your regular password
- Make sure 2FA is enabled on your Google account
- Visit: https://myaccount.google.com/apppasswords

**Import errors**
- Make sure you installed requirements: `pip install -r requirements.txt`

**Permission errors**
- Delete `token.pickle` and re-authorize when prompted

## Future Enhancements

Some ideas for later:
- Add due dates to tasks
- Parse dates from filenames
- Support for different timezones
- GitHub Action for auto-sync
- Clear old events option

