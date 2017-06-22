## Clone
Performs a bare-bones clone of an existing issue.  The following fields are cloned into a new issue: Project, Issue Type (task, story, etc), Assignee, Reporter, Priority, Fix Versions, Description, Components and Affected Versions.

NOTE: This entire project is based on EXP issues - and in particular Stories and Tasks.  No promises right now about it working for bugs, epics or features.

The user will be prompted to provide two fields: Work Allocation Label and Summary.  If desirable the user can just hit enter and default to the cloned issue summary.  WA-label was added because I get annoyed at how often I forget to put one on.

Subtasks are also cloned - they will clone hour estimates as well.

Usage: ```python3 clone.py -c <jira number>```

Example: ```python3 clone.py -c EXP-1234```

Do yourself a favor and make an alias.  The output will contain a link of the newly created issue.  MAC USERS: To open a browser directly from a link in terminal perform a Command-double click.

### Additional arguments for Clone

#### Replace

```-r <any string>``` replaces the text JIRA_TO_REPLACE in both the summary and description with the string provided in the argument.  I use this for cloning tasks that reference other tickets.  For example when we receive a security vulnerability (OPI) I always reference the OPI in a fresh EXP.  This allows me to not have to open Jira to do that.

Usage: ```python3 clone.py -c <jira to clone> -r <jira to reference>```

Example: ```python3 clone.py -c EXP-1234 -r OPI-5678```

#### Properties file

```-p <config properties location>``` Specifies the location of your configuration file. If nothing is provided then config.properties is used. At a minimum a config file must be present that has a single line: jira_host=<your host>

Usage: ```python3 clone.py -c EXP-1234 -p custom_config.properties```

#### Skip forced label

```-l``` Don't force a label for this jira

Example: ```python3 clone.py -c EXP-1234 -l```

#### Enter password

```-e``` Force me to enter a password. By default the system will look in the config file for a username and password entry. However it ban be forced to ask for a username / password - in which case it does not look in the config file.


## Cleanup

The following cleanup is performed against the specified jira:

1 - Loops through all subtasks and removes the prefix "CLONE - " from the beginning of each subtask.

2 - Loops through all the issue links and deletes them if they are of type "Cloners" - which is useful for cleaning up the "is a clone of" link. 

3 - Forces the jira to have a label assigned to it from the Work Allocation list of labels.

Usage: ```python3 clone.py -j <jira number>```

Example: ```python3 clone.py -j EXP-1234```

NOTE: You will be prompted for your jira username/password after executing
