# The Daily Digest: Setup Guide

Every morning your Kindle receives a newspaper-style PDF. It opens with **Top Stories**, then four topic sections: **France**, **Latin America**, **Middle East**, and **Gangs**. A story that appears under Top Stories is not repeated in a topic section.

Sources are prioritized: **AP News first, then The Guardian, then BBC and NPR.** This order applies to Top Stories and inside every topic section. Guardian stories in the topic sections show a headline, standfirst, and opening paragraph. Everything else shows a short excerpt and a link. AP stories are mostly a headline and a link, because AP doesn't offer excerpts; when another source covers the same story, its excerpt is borrowed and labeled ("Excerpt from ..."). When several sources cover the same story, it is shown once, from the highest-priority source, with the others listed under it ("Also reported by ...").

Each run also publishes a **web edition**: the same digest as a web page with links, at a web address you can open on any device (see Part 9).

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
| `HTML_EMAIL_TO` | address to email the full web edition to | No |

Once saved, GitHub hides these values. You can replace them but never view them again.

## Part 6: Upload the program

1. In your repository, click **Add file**, then **Upload files**.
2. Drag in `daily_news_kindle.py`, `requirements.txt`, and `INSTRUCTIONS.md`.
3. Click **Commit changes**.

## Part 7: Add the schedule file (version 15)

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
- *AP News missing*: open the run, then the **Build the digest and send it to Kindle** step. Near the top, one line per feed reads like `Feed check: AP News #1: 20 items (HTTP 200)`. If every AP line says 0 items, AP's sources are blocking the request that day. Copy those lines to me and I'll adjust. The digest still sends without AP.
- *Nothing on the Kindle*: your Gmail address isn't on the Kindle's approved list.

## Part 9: Put the web edition online (GitHub Pages)

Every morning the digest is also published to a web address like `https://YOUR-USERNAME.github.io/daily-digest/`. Bookmark it on your phone and computer.

**Read this first: the page is public.** On a free GitHub account, Pages works only for public repositories. That means anyone who has the link can open the page, and anyone can see the repository's files. To reduce the exposure:

- The page shows headlines, the publishers' short excerpts, Guardian standfirsts and opening paragraphs, and links to the full stories. The Guardian's developer key is meant for non-commercial use with credit to the Guardian, and the page includes that credit. Keep the page free of ads and don't charge for it. Check the Guardian's Open Platform terms if you plan to change that.
- The page asks search engines not to list it. This is a request, not protection, so don't treat the address as private.
- Your secrets (Kindle address, email, passwords, API key) stay hidden even in a public repository. GitHub never shows their values, and the program no longer prints your addresses in the run log.

**Step 1: Check the repository before making it public**

Open the repository's main page and look at the file list. It should contain only: `daily_news_kindle.py`, `requirements.txt`, `INSTRUCTIONS.md`, `last_sent.txt`, and the `.github` folder. If you ever uploaded a `.env` file or anything with a password or personal address, don't make this repository public. Create a new repository instead, upload the v14 files, and add the secrets again.

**Step 2: Update the files**

Replace `daily_news_kindle.py` and `.github/workflows/daily-news.yml` with the v14 versions. Open each file, click the pencil icon, select all, paste the new contents, and click **Commit changes**.

**Step 3: Make the repository public**

1. Click **Settings**, then scroll to the **Danger Zone** at the bottom of General.
2. Click **Change visibility**, then **Make public**, and confirm.

**Step 4: Turn on Pages**

1. In Settings, click **Pages** in the left panel.
2. Under **Build and deployment**, set **Source** to **GitHub Actions**.

**Step 5: Publish the first edition**

1. Click the **Actions** tab, then **Daily Digest to Kindle**, then **Run workflow**.
2. When both jobs show a green checkmark (the second one is called **deploy**), open the **deploy** job. It shows your page's web address. You can also find it in Settings, then Pages.

This run sends a digest to your Kindle as well. After that, the page updates by itself each morning.

**Taking it offline:** in Settings, then Pages, unpublish the site, or make the repository private again.

**Optional: email the web edition to yourself.** Add a secret called `HTML_EMAIL_TO` with the address that should receive it. Each morning that address gets an email showing the web edition, with the .html file attached. Leave the secret out and no email is sent.

If the web edition can't be built or published, the digest still goes to your Kindle. The problem appears as a warning or a failed **deploy** job in the run log.

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
- **News sources:** edit `RSS_FEEDS` in the same file. AP shut down its own RSS feeds in 2024, so AP News is read through a Google News search limited to apnews.com (plus AP's official Flipboard feed as a backup, and one AP search for each of your topics). AP links open through Google News and forward to apnews.com.
- **Send it now:** go to the Actions tab and run the workflow manually.
- **Pause it:** in the Actions tab, click the workflow, then the **...** menu, then **Disable workflow**.

**Notes**
- A story is judged to be the same as another by comparing headline words, so two outlets covering one event are shown once. Occasionally two different stories are treated as the same, or the same story appears twice with very different headlines.
- Gang stories are checked first, so a story about gang violence in Haiti or a cartel attack in Mexico goes under Gangs, not the regional section.
- The Latin America section includes any story that mentions Latin America or one of its countries (all 20 Spanish- and Portuguese-speaking countries plus Haiti), or a common adjective such as "Brazilian" or "Mexican", even if the story also covers the United States. Puerto Rico and Guyana are not included. To change which countries count, edit the Latin America `pattern` and `guardian_query` in the SECTIONS list.
- Gang stories are matched on specific terms such as "gang violence," "gang members," "drug cartel," and MS-13. To change them, edit the Gangs `pattern` and `guardian_query` in the SECTIONS list.
- GitHub turns off scheduled jobs in repositories with no activity for 60 days. If the digest stops, check the Actions tab for a prompt to re-enable it.
- The Guardian text shown is its own standfirst and opening paragraph. Use the links to read the full stories on the Guardian's site.
- Google sorts AP results by relevance rather than time, and AP stories are limited to the last day. That suits a morning digest, but the AP order is Google's idea of the most important stories, not AP's own front page.
- Arabic and other non-Latin scripts may not display correctly in the PDF. English-language stories display normally.
