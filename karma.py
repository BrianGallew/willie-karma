#!/usr/bin/env python
# encoding: utf-8

"""
karma.py - A karma module for willie.
Copyright 2013, Timothy Lee <marlboromoo@gmail.com>
Licensed under the MIT License.
"""

import string
import willie

###############################################################################
# Setup the module
###############################################################################

MODULE = 'karma'
WHO = 'who'
KARMA = 'karma'
REASON = 'reason'
DEBUG_LEVEL = 'verbose'

feedback = None
byself = None
penalty = False

def debug_(tag, text, level):
    """Mimic willie.debug function for pytest to use.
    """
    print "[%s] %s" % (tag, text)

debug = debug_

def configure(config):
    """

    | [karma] | example | purpose |
    | ------- | ------- | ------- |
    | feedback | True | Notify by bot |
    | byself | False | Self (pro|de)mote |
    | penalty | False | Penalize self (pro|de)mote |

    """
    if config.option('Configure karma', False):
        config.add_option('karma', 'feedback', 'Notify by bot', True)
        config.add_option('karma', 'byself', 'Self (pro|de)mote')
        config.add_option('karma', 'penalty', 'Penalize self (pro|de)mote')

def setup(bot):
    """Setup the database, get the settings.

    :bot: willie.bot.Willie

    """
    #. get debug function
    global debug, feedback, byself, penalty
    debug = bot.debug if bot.debug else debug
    #. get settings
    feedback_, byself_, penalty_ = True, False, False

    if not bot: return

    try:
        config = getattr(bot.config, MODULE)
        feedback_ = config.feedback
        byself_ = config.byself
        penalty_ = config.penalty
    except Exception, e:
        pass
    feedback = feedback_
    byself = byself_
    penalty = penalty_
    #. check database
    if bot.db:
        if not getattr(bot.db, KARMA):
            try:
                bot.db.add_table(KARMA, [WHO, KARMA, REASON], WHO)
            except Exception, e:
                debug(MODULE, 'Table init fail - %s' % (e), DEBUG_LEVEL)
                raise e
    else:
        msg = "DB init fail, setup the DB first!"
        debug(MODULE, msg, DEBUG_LEVEL)
        raise ConfigurationError(msg)

###############################################################################
# Helper function
###############################################################################

def get_table(bot):
    """Return the table instance.

    :bot: willie.bot.Willie
    :returns: willie.db.Table

    """
    try:
        return getattr(bot.db, KARMA)
    except Exception:
        return None

def get_karma(table, who):
    """Get karma status from the table.

    :table: willie.db.Table instance
    :who: nickname of IRC user
    :returns: (karma, reason)

    """
    karma, reason = 0, str(None)
    try:
        karma, reason = table.get(who, (KARMA, REASON))
        karma = int(karma)
    except Exception, e:
        debug(MODULE, "get karma fail - %s." % (e), DEBUG_LEVEL)
    return karma, reason

def _update_karma(bot, table, who, reason, amount):
    """Update karma for specify IRC user.

    :bot: williw.bot.Willie
    :table: willie.db.Table
    :who: nickname of IRC user
    :reason: reason
    :amount: number

    """
    karma = get_karma(table, who)[0] + amount
    try:
        if karma == 0:
            table.delete(who)
            if feedback:
                bot.say("%s garbage collected" % (who, karma, reason))
        else:
            table.update(who, dict(karma=str(karma), reason=reason))
            if feedback:
                bot.say("%s: %s, reason: %s" % (who, karma, reason))
    except Exception, e:
        debug(MODULE, "update karma fail, e: %s" % (e), DEBUG_LEVEL)

###############################################################################
# Event & Command
###############################################################################

@willie.module.rule(r'^([a-zA-Z0-9_]+)((?:\+\+|--)+)\s*(.*)')
def meet_karma(bot, trigger):
    """Update karma status for specific IRC user.
    :bot: willie.bot.Willie
    :trigger: willie.bot.Willie.Trigger

    """
    table = get_table(bot)
    if not table: return

    (who, directions, reason) = trigger.groups()
    while who[-1] == "_": who = who[:-1]
    #. penalize people for trying to promote themselves.
    if penalty and who == trigger.nick:
        reason = 'Penalized for self-promotion'
        _update_karma(bot, table, who, reason, -1)
    #. not allow self (pro|de)mote
    if not byself:
        if who == trigger.nick:
            return
    #. update karma
    increment = directions.count('++') - directions.count('--')
    _update_karma(bot, table, who, reason, increment)

@willie.module.commands('karma')
def karma(bot, trigger):
    """Command to show the karma status for specify IRC user.
    """
    table = get_table(bot)
    if table:
        if trigger.group(2):
            who = trigger.group(2).strip().split()[0]
            karma, reason= get_karma(table, who)
            bot.say("%s: %s, reason: %s" % (who, karma, reason))
        else:
            bot.say(".karma <nick> - Reports karma status for <nick>.")
    else:
        bot.say("Setup the database first, contact your bot admin.")

