# The Daily Digest: Setup Guide

Every morning your Kindle receives a newspaper-style PDF. It opens with **Top Stories**, then four topic sections: **France**, **Latin America**, **Middle East**, and **Gangs**. A story that appears under Top Stories is not repeated in a topic section.

Sources are prioritized: **AP News first, then The Guardian, then BBC and NPR.** This order applies to Top Stories and inside every topic section. Guardian stories in the topic sections show a headline, standfirst, and opening paragraph. Everything else shows a short excerpt and a link. When several sources cover the same story, it is shown once, from the highest-priority source, with the others listed under it ("Also reported by ...").

Each run also builds a **web edition**: the same digest as a web page, with links, saved in your repository as `docs/index.html`. You can also have it emailed to you (see Part 9).

The job runs on GitHub's servers, so your computer can be off. Setup is done entirely in a web browser.

## Before you start

You need:
- A Kindle with its Send-to-Kindle email address (ends in @kindle.com)
- A Gmail account to send from
- A free GitHub account (github.com)
- A free Guardian API key (Part 2)

## Part 1: Allow your sending email on your Kindle

1. Go to amazon.com and open **Manage Your Content and Devices**.
2. Click **Preferences**, then scroll to **Personal Document Settings**.
3. Copy your Send-to-Kindle address (ends in @kindle.com). This is your **KINDLE_EMAIL**.
4. Under **Approved Personal Document E-mail List**, add your Gmail address. Amazon ignores documents from addresses not on this list.

## Part 2: Get a free Guardian API key

The program uses this to fetch recent Guardian stories.

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
2. Click **New repository secret** and add each of these, one at a time:

| Name | Value | Required? |
|---|---|---|
| `KINDLE_EMAIL` | your @kindle.com address | Yes |
| `SENDER_EMAIL` | your Gmail address | Yes |
| `SMTP_PASSWORD` | the 16-character App Password | Yes |
| `GUARDIAN_API_KEY` | the key from Part 2 | Yes, for Guardian stories |
| `HTML_EMAIL_TO` | address to email the web edition to | No |

Once saved, GitHub hides these values. You can replace them but never view them again.

## Part 6: Upload the program

1. In your repository, click **Add file**, then **Upload files**.
2. Drag in `daily_news_kindle.py`, `requirements.txt`, and `INSTRUCTIONS.md`.
3. Click **Commit changes**.

## Part 7: Add the schedule file (version 11)

The schedule file is in the `.github/workflows` folder of the package. Because that folder name starts with a dot, macOS hides it by default. Press Cmd+Shift+. in Finder to show hidden folders, or copy the text from the package.

1. In your repository, click **Add file**, then **Create new file**.
2. In the file name box, type exactly: `.github/workflows/daily-news.yml`
   Typing the slashes creates the folders automatically.
3. Paste in the contents of `daily-news.yml` from the package.
4. Click **Commit changes**.

If the file already exists, open it, click the pencil icon, and replace the contents.

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
- *Guardian stories missing*: the Guardian key is missing or mistyped. Headlines still send.
- *Nothing on the Kindle*: your Gmail address isn't on the Kindle's approved list.

## Part 9 (optional): Read the web edition

Every run saves the web edition as `docs/index.html` in your repository. There are three ways to read it:

**Email it to yourself (easiest).** Add a secret called `HTML_EMAIL_TO` (Settings, Secrets and variables, Actions) with the address that should receive it. Each morning that address gets an email showing the web edition, with the .html file attached to open in a browser. Leave the secret out and no email is sent.

**Download it from GitHub.** Open the repository, go to `docs`, click `index.html`, then click the download icon. Save it and open it in your browser. GitHub shows only the page's source code when you view the file there, so download it to see the formatted page.

**Host it as a web page (GitHub Pages).** Go to Settings, then Pages, choose the `main` branch and the `/docs` folder, and save. GitHub gives you a web address that always shows the latest edition. Be aware that on a free GitHub account, Pages works only for **public** repositories. A public repository, and the page itself, would be visible to anyone, and the page contains news excerpts you don't own. I recommend email or download instead unless you have a paid plan with private Pages.

If the web edition can't be saved or emailed, the digest still goes to your Kindle. The problem appears as a warning in the run log.

## Daily use

Nothing else is needed. The digest is sent at 6:30 AM Paris time, and the schedule adjusts for daylight saving time automatically, so you never need to edit the time.

**Backup run:** a second run starts 30 minutes after the first. It sends only if today's digest hasn't gone out yet, so a late or skipped GitHub run is covered without sending you two digests.

**Record of sending:** after each successful send, the job saves the date in a file called `last_sent.txt` in your repository. Don't delete it. Running the workflow by hand always sends a digest, even if one has already gone out that day.

## Making changes

- **Section topics:** open `daily_news_kindle.py`, click the pencil icon, and edit the `SECTIONS` list. Each section has a `pattern` (the words that send a story there) and a `guardian_query` (what to search the Guardian for).
- **Guardian stories per section:** change `guardian_stories` in each section.
- **Headlines per section:** change `MAX_BRIEFS_PER_SECTION`.
- **Source priority:** edit `SOURCE_ORDER` in the same file. The first name has the highest priority.
- **Number of top stories:** edit `TOP_PER_SOURCE`, which sets how many lead stories each source can contribute to Top Stories. The default is 4 from AP, 3 from the Guardian, 2 from BBC, and 1 from NPR.
- **Other Headlines section:** set `INCLUDE_OTHER_HEADLINES = True` to add a final section for stories that fit no topic. It is off by default.
- **News sources:** edit `RSS_FEEDS` in the same file. AP News is included through AP's official Flipboard feed, because AP's own RSS feeds were discontinued in 2024.
- **Send it now:** go to the Actions tab and run the workflow manually.
- **Pause it:** in the Actions tab, click the workflow, then the **...** menu, then **Disable workflow**.

**Notes**
- A story is judged to be the same as another by comparing headline words, so two outlets covering one event are shown once. Occasionally two different stories are treated as the same, or the same story appears twice with very different headlines.
- Gang stories are checked first, so a story about gang violence in Haiti or a cartel attack in Mexico goes under Gangs, not the regional section.
- The Latin America section includes any story that mentions Latin America or one of its countries (all 20 Spanish- and Portuguese-speaking countries plus Haiti), or a common adjective such as "Brazilian" or "Mexican", even if the story also covers the United States. Puerto Rico and Guyana are not included. To change which countries count, edit the Latin America `pattern` and `guardian_query` in the SECTIONS list.
- Gang stories are matched on specific terms such as "gang violence," "gang members," "drug cartel," and MS-13. To change them, edit the Gangs `pattern` and `guardian_query` in the SECTIONS list.
- GitHub turns off scheduled jobs in repositories with no activity for 60 days. If the digest stops, check the Actions tab for a prompt to re-enable it.
- The text shown is the Guardian's own standfirst and opening paragraph, for your personal reading. Use the links to read the full stories on the Guardian's site.
- Arabic and other non-Latin scripts may not display correctly in the PDF. English-language stories display normally.
