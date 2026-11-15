# Daily News to Kindle: Setup Guide

Your Kindle receives a PDF news digest every morning. The job runs on GitHub's servers, so your computer can be off. Everything in setup is done in a web browser.

## Before you start

You need:
- A Kindle with its Send-to-Kindle email address (ends in @kindle.com)
- An email account to send from. These instructions use Gmail.
- A free GitHub account (github.com)

## Part 1: Allow your sending email on your Kindle

1. Go to amazon.com and open **Manage Your Content and Devices**.
2. Click **Preferences**, then scroll to **Personal Document Settings**.
3. Copy your Send-to-Kindle email address (ends in @kindle.com). This is your **KINDLE_EMAIL**.
4. Under **Approved Personal Document E-mail List**, add your sending email address. Amazon ignores documents from addresses not on this list.

## Part 2: Create a Gmail App Password

Gmail doesn't allow ordinary passwords for automated sending, so you need a separate App Password.

1. Turn on 2-Step Verification at myaccount.google.com/security if it isn't already on.
2. Go to myaccount.google.com/apppasswords.
3. Name it "Kindle News" and click **Create**.
4. Copy the 16-character password. This is your **SMTP_PASSWORD**. You won't see it again, so keep this page open until Part 4 is finished.

## Part 3: Create your GitHub repository

1. Go to github.com and sign in.
2. Click the **+** at the top right, then **New repository**.
3. Name it `daily-news-kindle` and set it to **Private**.
4. Click **Create repository**.

## Part 4: Add your secrets

1. In your repository, click **Settings**, then **Secrets and variables**, then **Actions**.
2. Click **New repository secret** and add these three, one at a time:

| Name | Value |
|---|---|
| `KINDLE_EMAIL` | your @kindle.com address |
| `SENDER_EMAIL` | your Gmail address |
| `SMTP_PASSWORD` | the 16-character App Password |

Once saved, GitHub hides these values. You can't view them again, only replace them.

## Part 5: Upload the program

1. In your repository, click **Add file**, then **Upload files**.
2. Drag in `daily_news_kindle.py`, `requirements.txt`, and this `INSTRUCTIONS.md` file.
3. Click **Commit changes**.

## Part 6: Add the schedule file

1. Click **Add file**, then **Create new file**.
2. In the file name box, type exactly: `.github/workflows/daily-news.yml`
   Typing the slashes creates the folders automatically.
3. Open `daily-news.yml` from the downloaded package, copy everything, and paste it into the editor.
4. Click **Commit changes**.

## Part 7: Test it

1. Click the **Actions** tab.
2. In the left panel, click **Daily News to Kindle**.
3. Click **Run workflow**, then the green **Run workflow** button.
4. Wait about a minute and refresh the page.
   - **Green checkmark:** it worked. The PDF should reach your Kindle within a few minutes.
   - **Red X:** click the run and open the **Build the digest and send it to Kindle** step to read the error.

Common problems:
- *"Missing required settings"*: a secret name is misspelled. The names must match exactly.
- *Authentication error*: you used your normal Gmail password. Use the App Password.
- *Nothing on the Kindle*: the sending address isn't on your Kindle's approved list.

## Daily use

Once set up, nothing else is needed. The digest is sent every morning at 6:30 AM New York time. GitHub sometimes starts scheduled jobs a few minutes late.

**Clock changes:** the schedule is in UTC, so the delivery time shifts by one hour when daylight saving time starts or ends. To keep 6:30 AM local time year-round, edit the `cron` line in `daily-news.yml`:
- Winter (EST): `30 11 * * *`
- Summer (EDT): `30 10 * * *`

## Making changes

- **Change the news sources:** open `daily_news_kindle.py`, click the pencil icon, and edit the `FEEDS` section. Most news sites offer RSS feeds, so search "[site name] RSS feed".
- **Change article count or summary length:** edit `ITEMS_PER_FEED` and `SUMMARY_CHARS` in the same place.
- **Send it now:** go to the Actions tab and run the workflow manually.
- **Pause it:** in the Actions tab, click the workflow, then the **...** menu, then **Disable workflow**.

**Note:** GitHub turns off scheduled jobs in repositories with no activity for 60 days. If the digest stops, check the Actions tab for a prompt to re-enable it.
