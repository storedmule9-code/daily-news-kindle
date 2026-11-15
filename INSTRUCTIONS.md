# The Daily Digest: Setup Guide

Every morning your Kindle receives a newspaper-style PDF with four sections: France, Latin America, Middle East, and Gangs. Each section opens with full Guardian articles, followed by short headlines from BBC, NPR, and The Guardian. Stories that don't match a section appear under Other Headlines at the end.

The job runs on GitHub's servers, so your computer can be off. Setup is done entirely in a web browser.

## Before you start

You need:
- A Kindle with its Send-to-Kindle email address (ends in @kindle.com)
- A Gmail account to send from
- A free GitHub account (github.com)
- A free Guardian API key (Part 2 below)

## Part 1: Allow your sending email on your Kindle

1. Go to amazon.com and open **Manage Your Content and Devices**.
2. Click **Preferences**, then scroll to **Personal Document Settings**.
3. Copy your Send-to-Kindle address (ends in @kindle.com). This is your **KINDLE_EMAIL**.
4. Under **Approved Personal Document E-mail List**, add your Gmail address. Amazon ignores documents from addresses not on this list.

## Part 2: Get a free Guardian API key

This lets the program download full Guardian articles.

1. Go to open-platform.theguardian.com/access.
2. Fill in the short form and choose the **Developer** (free) option.
3. The key arrives by email. Copy it. This is your **GUARDIAN_API_KEY**.

## Part 3: Create a Gmail App Password

Gmail doesn't allow ordinary passwords for automated sending, so you need a separate App Password.

1. Turn on 2-Step Verification at myaccount.google.com/security if it isn't already on.
2. Go to myaccount.google.com/apppasswords.
3. Name it "Daily Digest" and click **Create**.
4. Copy the 16-character password. This is your **SMTP_PASSWORD**. Google shows it only once, so keep the page open until Part 5 is done.

## Part 4: Create your GitHub repository

1. Go to github.com and sign in.
2. Click the **+** at the top right, then **New repository**.
3. Name it `daily-digest` and set it to **Private**.
4. Click **Create repository**.

## Part 5: Add your secrets

1. In your repository, click **Settings**, then **Secrets and variables**, then **Actions**.
2. Click **New repository secret** and add each of these four, one at a time:

| Name | Value |
|---|---|
| `KINDLE_EMAIL` | your @kindle.com address |
| `SENDER_EMAIL` | your Gmail address |
| `SMTP_PASSWORD` | the 16-character App Password |
| `GUARDIAN_API_KEY` | the key from Part 2 |

Once saved, GitHub hides these values. You can replace them but never view them again.

## Part 6: Upload the program

1. In your repository, click **Add file**, then **Upload files**.
2. Drag in `daily_news_kindle.py`, `requirements.txt`, and `INSTRUCTIONS.md`.
3. Click **Commit changes**.

## Part 7: Add the schedule file

The schedule file is in the `.github/workflows` folder of the package. Because that folder name starts with a dot, macOS hides it by default. Press Cmd+Shift+. in Finder to show hidden folders, or copy the text below.

1. In your repository, click **Add file**, then **Create new file**.
2. In the file name box, type exactly: `.github/workflows/daily-news.yml`
   Typing the slashes creates the folders automatically.
3. Paste in the contents of `daily-news.yml` from the package.
4. Click **Commit changes**.

## Part 8: Test it

1. Click the **Actions** tab.
2. In the left panel, click **Daily Digest to Kindle**.
3. Click **Run workflow**, then the green **Run workflow** button.
4. Wait about a minute and refresh the page.
   - **Green checkmark:** it worked. The digest should reach your Kindle within a few minutes.
   - **Red X:** click the run and open the **Build the digest and send it to Kindle** step to read the error.

Common problems:
- *"Missing required settings"*: a secret name is misspelled. The names must match exactly.
- *Authentication error*: you used your normal Gmail password. Use the App Password.
- *Full articles missing, headlines present*: the Guardian key is missing or mistyped. The digest still sends without it.
- *Nothing on the Kindle*: your Gmail address isn't on the Kindle's approved list.

## Daily use

Nothing else is needed. The digest is sent at 6:30 AM New York time. GitHub sometimes starts scheduled jobs a few minutes late.

**Clock changes:** the schedule runs on UTC, so the delivery time shifts by an hour when daylight saving time starts or ends. To keep 6:30 AM local time year-round, edit the `cron` line in `daily-news.yml`:
- Winter (EST): `30 11 * * *`
- Summer (EDT): `30 10 * * *`

## Making changes

- **Section topics:** open `daily_news_kindle.py`, click the pencil icon, and edit the `SECTIONS` list. Each section has a `pattern` (the words that send a story there) and a `guardian_query` (what to search the Guardian for).
- **Number of full articles:** change `full_articles` in each section.
- **Headlines per section:** change `MAX_BRIEFS_PER_SECTION`.
- **News sources:** edit `RSS_FEEDS` in the same file.
- **Send it now:** go to the Actions tab and run the workflow manually.
- **Pause it:** in the Actions tab, click the workflow, then the **...** menu, then **Disable workflow**.

**Notes**
- Sections are checked in order, so a story about a cartel in Mexico goes under Latin America, not Gangs.
- GitHub turns off scheduled jobs in repositories with no activity for 60 days. If the digest stops, check the Actions tab for a prompt to re-enable it.
- The Guardian API key is free for personal use. Full articles are for your own reading, not for redistribution.
- Arabic and other non-Latin scripts may not display correctly in the PDF. English-language stories display normally.
