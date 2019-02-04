Yarnbot
=======

Yarnbot is a Slack-bot that knows some yarn-working things, and can search
Ravelry for patterns, yarn, or user favorites.


Yarnbot understands:
 * &lt;7 character abbreviations
 * Yarn weights
 * Needle/Hook sizes (say 'US 10', '5mm', 'Crochet L', etc)
 * Basic arithmetic expressions
 * **weights**: List all yarn weights
 * **ravelry favorites** &lt;Ravelry Username&gt;
 * **ravelry favorites** &lt;Ravelry Username&gt; **tagged** &lt;tag&gt;
 * **ravelry search** &lt;search terms&gt;: Search patterns
 * **ravelry yarn** &lt;search terms&gt;: Search yarn
 * **ravelry yarn similar to** &lt;search terms&gt;: Find similar yarn
 * **info**: Yarnbot info
 * **help**: Help text

## Running

Before anything else will work, you will need to create a bot in Slack. In your team's app management section, create a custom integration and add a bot configuration. The API Token available there is the SLACK_API_KEY referenced below.

Use a script such as the provded example to set the various access keys and run the client. It will try to stay connected to slack until you tell it to `go to sleep`, which will cause it to disconnect gracefully.

Yarnbot will create a log file named `yarnbot.log` in the current directory. By default, it logs at the INFO level, but that can be changed by altering the logging setup at the beginning of `yarnbot.py`.

As it runs, it keeps track of users it has seen, and saves them in `known_users.pkl`. Please note that is a python pickle file.

### Access Tokens

Yarnbot requires a Slack API key, taken from the SLACK_API_KEY environment variable, as well as Ravelry OAuth1 keys, taken from RAV_ACC_KEY and RAV_SEC_KEY.

## Screenshots

Some typical yarnbot commands

![yarnbot commands](https://imgur.com/1cPZXV1.png)

Ravelry search results show short summaries of each pattern. Clicking the pattern will take you to Ravelry to see details.

![yarnbot ravelry search](https://imgur.com/hx5Yo7x.png)

You can also search for yarn...

![yarnbot ravelry yarn](https://imgur.com/efIld1B.png)

...and find similar yarn.

![yarnbot ravelry yarn similar to](https://imgur.com/gfA9aOC.png)

