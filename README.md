# Today News

Bilingual Hindi + English static news site built with Jekyll and GitHub Pages.

Live URL: https://bhanupratapsingh5697-lang.github.io

## Features
- Responsive newspaper-style homepage and article pages.
- Client-side search and category filters.
- Manual Markdown publishing in the _posts folder.
- Hourly RSS imports using GitHub Actions, plus manual workflow dispatch.
- RSS feed, SEO metadata and sitemap. No backend, database, paid hosting or API key.

## Manual publishing
Create a file in _posts named YYYY-MM-DD-your-story.md. Add YAML front matter with layout: post, title, date, category, author and image. Write your original article in Markdown, then commit and push to main.

## Automatic publishing
Open Actions, select Import RSS news and click Run workflow. It also runs hourly. Edit the FEEDS list in scripts/import_rss.py to add or remove sources. Imported posts contain short summaries and links to original publishers, not full copied articles.

## First-time setup
Open repository Settings > Pages. Set Build and deployment Source to GitHub Actions. Save. Then check Actions for the deployment workflow. Under Settings > Actions > General > Workflow permissions, allow read and write permissions if the RSS workflow cannot push commits.

## Editorial and operational notes
RSS summaries can be incomplete or inaccurate. Review stories for accuracy, context and suitability. Respect publisher terms and attribution. Scheduled GitHub jobs may be delayed. Static GitHub Pages does not provide user accounts, comments or a private admin dashboard.
