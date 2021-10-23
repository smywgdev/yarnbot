'''
    Yarnbot - Slack bot for yarn working

    Copyright (C) 2017  Nigel D. Stepp

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along
    with this program; if not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

    Nigel Stepp <stepp@atistar.net>
'''

import os
import sys
import time
import string
import random
import pickle
import re
import logging

from typing import Any, Dict, List, Optional

from slack_bolt import App, Say
from slack_sdk.web.client import WebClient

from .conversations import EaseConversation
from .state import app_state

from . import data, __version__
from .ravelry import (ravelry_api, ravelry_api_yarn,
    ravelry_pattern, ravelry_yarn, yarn_distance)

Event = Optional[Dict[str, Any]]

USERDB_FILENAME = 'known_users.pkl'

app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

def strip_punc(s: str) -> str:
    return str(s).translate(str.maketrans('','', string.punctuation)).strip()


def start_conversation(conv_name: str, user_id: str) -> str:
    '''
    Start a conversation for a user.

    Parameters:
        conv_name (str): Conversation name.
        user_id (str): Start a conversation with this user

    Returns:
        str: The initial response
    '''

    conv = None

    if conv_name == 'ease':
        conv = EaseConversation()

    if conv is None:
        return "Something funny happened trying to start a conversation :/"


    msg = "Starting a conversation with yarnbot, just say 'cancel' to cancel\n"

    reply = conv.step('')

    if reply is not None:
        (reply_msg,terminal) = reply

    if not terminal:
        app_state.conversations[user_id] = conv

    msg += reply_msg

    return msg

def continue_conversation(user_id: str, msg: str) -> str:
    '''
    Continue already started conversation.

    Parameters:
        user_id (str): User we are talking to.
        msg (str): The user's last response

    Returns:
        str: Our next response
    '''

    if msg == 'cancel':
        del app_state.conversations[user_id]
        return 'Ok, conversation canceled'

    if user_id not in app_state.conversations:
        return 'Hmm, this conversation seems to be over :/'

    conv = app_state.conversations[user_id]

    reply = conv.step(msg)

    if reply is not None:
        (reply_msg, terminal) = reply

    if reply is None or terminal:
        del app_state.conversations[user_id]

    return reply_msg

@app.event('message')
def proc_msg(event: Event, say: Say, client: WebClient) -> Optional[str]:
    '''
    Process message events.

    Parameters:
        event (Event): The event
        say (Say): say handler
        client (WebClient): web api client

    Returns:
        Optional[str]: None unless it's time to quit, then 'quit'

    Note:
        This still needs to be updated for Bolt; broken out into
        individual message responders, and update return value
        (at the moment, the 'quit' return does nothing)
    '''

    reply = None

    if event is None:
        return None

    evt = event

    logging.debug(str(evt))

    if 'user' not in evt:
        return None

    user_id = evt['user']
    channel_id = evt['channel']
    msg_text = evt['text']

    if user_id == app_state.bot_user_id:
        return None

    app_state.message_count += 1

    direct_msg = channel_id.startswith('D')

    if ':sheep:' in msg_text:
        say("Did someone say :sheep:?")
        return None

    if user_id in app_state.conversations:
        reply = continue_conversation(user_id, msg_text)
        if reply is not None:
            say(reply)
        return None

    if app_state.bot_user_ref in msg_text:
        direct_msg = True
        msg_parts = msg_text.split(app_state.bot_user_ref,1)
        msg_parts_stripped = [strip_punc(m) for m in msg_parts]
        if len(msg_parts_stripped[1]) > 0:
            msg_text = msg_parts_stripped[1]
            msg_orig = msg_parts[1]
        else:
            msg_text = msg_parts_stripped[0]
            msg_orig = msg_parts[0]

        if len(msg_text) <= 0:
            return None
        if not msg_text[0].isalnum():
            msg_text = msg_text[1:].strip()
    else:
        msg_orig = msg_text

    if not direct_msg:
        return None

    msg_lower = msg_text.lower()
    msg_stripped = str(msg_lower).translate(str.maketrans('','','.,!?:;'))

    if 'ease' in msg_stripped and 'help' in msg_stripped:
        reply = start_conversation('ease',user_id)
    elif msg_stripped in data.acronyms:
        reply = "*{0}* is {1}".format(msg_text, data.acronyms[msg_stripped]['desc'])
        if data.acronyms[msg_stripped]['url'] is not None:
            reply += "\n<{0}|more info>".format(data.acronyms[msg_stripped]['url'])
    elif msg_stripped == 'help':
        reply = "I understand:\n"
        reply += "  &lt;7 character abbreviations\n"
        reply += "  Yarn weights\n"
        reply += "  Needle/Hook sizes (say 'US 10', '5mm', 'Crochet L', etc)\n"
        reply += "  Basic arithmetic expressions\n"
        reply += "  *weights*: List all yarn weights\n"
        reply += "  *needles* or *hooks*: List all needles/hooks\n"
        reply += "  *ravelry favorites* &lt;Ravelry Username&gt;\n"
        reply += "  *ravelry favorites* &lt;Ravelry Username&gt; *tagged* &lt;tag&gt;\n"
        reply += "  *ravelry search* &lt;search terms&gt;: Search patterns\n"
        reply += "  *ravelry yarn* &lt;search terms&gt;: Search yarn\n"
        reply += "  *ravelry yarn similar to* &lt;search terms&gt;: Find similar yarn\n"
        reply += "  *info*: Yarnbot info\n"
        reply += "  *help*: This text\n\n"
        reply += "I also know how to have convsersations about:"
        reply += "  *Ease*: Say anything to me with 'help' and 'ease' and I will help\n"
        reply += "          you calculate ease and gauge in different ways."
    elif msg_stripped in data.yarn_weights:
        yarn_info = data.yarn_weights[msg_stripped]
        reply = "*{0}* weight yarn is number {1}, typically {2} stitches per 4 in., {3}-ply, {4} wraps per inch".format(msg_stripped,
            yarn_info['number'],
            yarn_info['gauge'],
            yarn_info['ply'],
            yarn_info['wpi'])
    elif msg_lower.startswith('us '):
        m = re.match('^us ([0-9.]+)', msg_lower)
        if m:
            size = m.groups()[0]
            if size in data.needles_by_us:
                reply = "*US size {0}* is {1} mm, UK {2}, Crochet {3}".format(size,
                        data.needles_by_us[size]['metric'],
                        data.needles_by_us[size]['uk'],
                        data.needles_by_us[size]['crochet'])
            else:
                reply = "US {0} doesn't seem to be a standard size.".format(size)
    elif msg_lower.startswith('uk '):
        m = re.match('^uk ([0-9.]+)', msg_lower)
        if m:
            size = m.groups()[0]
            if size in data.needles_by_uk:
                reply = "*UK size {0}* is {1} mm, US {2}, Crochet {3}".format(size,
                        data.needles_by_uk[size]['metric'],
                        data.needles_by_uk[size]['us'],
                        data.needles_by_uk[size]['crochet'])
            else:
                reply = "UK {0} doesn't seem to be a standard size.".format(size)
    elif re.match('^[0-9.]+ *mm', msg_lower):
        m = re.match('^([0-9.]+) *mm', msg_lower)
        if m:
            size = "{0:.2f}".format(float(m.groups()[0]))
            if size in data.needles_by_metric:
                reply = "*{0} mm* needles/hooks are US {1}, UK {2}, Crochet {3}".format(size,
                        data.needles_by_metric[size]['us'],
                        data.needles_by_metric[size]['uk'],
                        data.needles_by_metric[size]['crochet'])
            else:
                reply = "{0} mm doesn't seem to be a standard size.".format(size)
    elif msg_lower.startswith('crochet '):
        m = re.match('^crochet ([a-z])', msg_lower)
        if m:
            size = m.groups()[0].upper()
            if size in data.needles_by_crochet:
                reply = "*Crochet {0}* is {1} mm, US {2}, UK {3}".format(size,
                        data.needles_by_crochet[size]['metric'],
                        data.needles_by_crochet[size]['us'],
                        data.needles_by_crochet[size]['uk'])
            else:
                reply = "Crochet {0} doesn't seem to be a standard size.".format(size)

    elif msg_stripped == 'weights':
        reply = "These are all of the yarn weights I know about:\n"
        for w in sorted(data.yarn_weights.keys(),key=lambda x: data.yarn_weights[x]['number']):
            reply += "  *{0}*: {1} ply, {2} wpi, {3} per 4 in. typical gauge, number {4}\n".format(w,
                     data.yarn_weights[w]['ply'],data.yarn_weights[w]['wpi'],
                     data.yarn_weights[w]['gauge'],data.yarn_weights[w]['number'])

    elif msg_stripped == 'needles' or msg_stripped == 'hooks':
        reply = "These are all of the needles/hooks I know about:\n"
        for size in sorted(data.needles_by_metric.keys(),key=float):
            reply += "*{0} mm* needles/hooks are US {1}, UK {2}, Crochet {3}\n".format(size,
                    data.needles_by_metric[size]['us'],
                    data.needles_by_metric[size]['uk'],
                    data.needles_by_metric[size]['crochet'])

    elif msg_lower.startswith('welcome '):
        m = re.match('^welcome <@(u[a-z0-9]+)>', msg_lower)
        logging.info('Got welcome command: {0} {1}'.format(msg_lower,m))

        if m:
            to_user_id = m.groups()[0].upper()
            logging.info('welcome from {0} to {1}'.format(user_id,to_user_id))
            welcome_msg(to_user_id, user_id)
            reply = "Welcome message sent!"

    elif msg_stripped == 'runningconversations':
        try:
            convs = [ u + ': ' + c.name for (u,c) in app_state.conversations.items() ]
            reply = '\n'.join(convs)
        except:
            reply = "Couldn't list conversations"

    elif re.match('^[0-9+-/*. ()]+$', msg_orig.strip()):
        try:
            reply = '{0}'.format( eval(msg_orig.strip()) )
        except:
            reply = "Arithmetic evaluation error"

    # Ravelry subcommands
    elif msg_stripped.startswith('ravelry '):

        try:
            rav_cmd = msg_stripped.split()

            if rav_cmd[1] in ['yarn','yarns'] and rav_cmd[2] in ['similar','comparable'] and rav_cmd[3] == 'to':

                if 'force' in rav_cmd:
                    force_search = True
                    rav_cmd.remove('force')
                else:
                    force_search = False

                target_results, msg, parms = ravelry_api_yarn(rav_cmd[4:])

                num_yarns = target_results['paginator']['results']

                if not force_search and num_yarns > 5:
                    reply = 'That yarn description returned {0} results, which is probably'.format(num_yarns)
                    reply += ' too many for a good comparison. Try adding more search terms'
                    reply += ' (especially weight and fiber), or add "force" to your search'
                    reply += ', which will just pick the top result.'
                    say(reply)
                    return None
                elif num_yarns < 1:
                    reply = "That yarn description didn't return any results :disappointed:"
                    say(reply)
                    return None

                target_yarn = target_results['yarns'][0]

                detail_results = ravelry_api('yarns/{0}.json'.format(target_yarn['id']), {'id': target_yarn['id']})
                target_yarn_detail = detail_results['yarn']
                target_fibers = [ x['fiber_type']['name'].lower().replace(' ','-') for x in target_yarn_detail['yarn_fibers'] ]

                target_weight = target_yarn_detail['yarn_weight']['name'].lower().replace(' ','-')

                similar_results, msg, parms = ravelry_api_yarn(target_fibers + [target_weight], 50)

                if similar_results['paginator']['results'] < 1:
                    reply = 'No results.... somehow'
                    say(reply)
                    return None

                # Sort results by yarn comparison

                similar_sorted = sorted(similar_results['yarns'], key=lambda x: yarn_distance(target_yarn, x))
                attachments = []
                for info in similar_sorted[0:5]:

                    mach_wash = info['machine_washable'] if 'machine_washable' in info else None
                    if mach_wash is None or not mach_wash:
                        mach_wash = 'No'
                    else:
                        mach_wash = 'Yes'

                    organic = info['organic'] if 'organic' in info else None
                    if organic is None or not organic:
                        organic = 'No'
                    else:
                        organic = 'Yes'

                    description = info['yarn_weight']['name']
                    if info['gauge_divisor'] is not None:
                        gauge_range = []
                        if info['min_gauge'] is not None:
                            gauge_range.append(str(info['min_gauge']))
                        if info['max_gauge'] is not None:
                            gauge_range.append(str(info['max_gauge']))

                        description += ', {0} sts = {1} in'.format(' to '.join(gauge_range), info['gauge_divisor'])

                    description += ', {0} g, {1} yds'.format(info['grams'],info['yardage'])

                    attachment = dict()
                    attachment['fallback'] = info['name']
                    attachment['color'] = '#36a64f'
                    attachment['author_name'] = info['yarn_company_name']
                    attachment['title'] = info['name']
                    if info['discontinued']:
                        attachment['title'] += ':skull:'

                    attachment['title_link'] = 'https://www.ravelry.com/yarns/library/' + info['permalink']
                    attachment['text'] = description
                    attachment['thumb_url'] = info['first_photo']['square_url']
                    attachment['fields'] = [ {'title':'Machine Washable', 'value': mach_wash, 'short': True},
                                             {'title':'Organic', 'value': organic, 'short': True} ]

                    attachments.append( attachment )

                msg = u"Yarn most similar to {0} {1} {2}-weight ({3})".format(target_yarn['yarn_company_name'],target_yarn['name'],target_weight,','.join(target_fibers))
                #attach_json = json.dumps( attachments )

                send_msg(client, channel_id, msg, attachments)

                return None

            elif rav_cmd[1] == 'yarn':

                (yarn_msg, attach) = ravelry_yarn(rav_cmd[2:])

                if yarn_msg is not None:
                    send_msg(client, channel_id, yarn_msg, attach)
                else:
                    say(':disappointed:')

                return None


            elif rav_cmd[1] == 'search':

                (rav_search_msg, attach) = ravelry_pattern(rav_cmd[2:])

                if rav_search_msg is not None:
                    send_msg(client, channel_id, rav_search_msg, attach)
                else:
                    say(':disappointed:')

                return None

            if rav_cmd[1] == 'favorites':
                fav_user = rav_cmd[2]
                parms = {'username':fav_user, 'page_size':'5'}
                msg = u"Most recent favorites for {0}".format(fav_user)
                if len(rav_cmd) > 3:
                    if rav_cmd[3] == 'tagged' and len(rav_cmd) > 4:
                        parms.update( {'tag': rav_cmd[4]} )
                        msg += u', tagged {0}'.format(rav_cmd[4])
                    else:
                        query = " ".join(rav_cmd[3:])
                        parms.update( {'query': query} )
                        msg += u', containing {0}'.format(query)
                rav_result = ravelry_api('/people/{0}/favorites/list.json'.format(fav_user), parms)

                if rav_result['paginator']['results'] == 0:
                    say(':disappointed:')
                    return None

                attachments = []
                for fav in rav_result['favorites']:

                    attachment = dict()
                    attachment['fallback'] = fav['favorited']['name']
                    attachment['color'] = '#36a64f'
                    attachment['title'] = fav['favorited']['name']
                    attachment['title_link'] = 'https://www.ravelry.com/patterns/library/' + fav['favorited']['permalink']

                    # Sometime not everything is available
                    try:
                        attachment['image_url'] = fav['favorited']['first_photo']['square_url']
                    except:
                        logging.warning(u'Ravelry result with missing info: {0}'.format(fav))
                    try:
                        attachment['author_name'] = fav['favorited']['designer']['name']
                    except:
                        logging.warning(u'Ravelry result with missing info: {0}'.format(fav))

                    attachments.append( attachment )

                client.chat_postMessage(channel=channel_id,
                    as_user=True,
                    text=msg,
                    attachments=attachments)
                return None

        except Exception as e:
            reply = 'Ravelry command error'
            tb_info = sys.exc_info()[2]
            if tb_info is not None:
                lineno = str(tb_info.tb_lineno)
            else:
                lineno = 'unknown'
            logging.warning('Ravelry error line {0}: {1}'.format(lineno,e) )

    elif msg_stripped == 'hello' or msg_stripped == 'hi' or msg_stripped.startswith('hello ') or msg_stripped.startswith('hi '):
        reply_ind = random.choice( range(len(data.greetings)) )
        reply = data.greetings[reply_ind]
    elif msg_stripped.startswith('good') and (msg_stripped.endswith('morning') or msg_stripped.endswith('afternoon') or msg_stripped.endswith('night') or msg_stripped.endswith('evening')):
        reply = ':kissing_heart:'
    elif msg_stripped == 'info':
        reply = "I'm yarnbot {0}, started on {1}.\n".format(__version__, time.ctime(app_state.start_time))
        reply += "I've processed {0} messages ({1} unknown).".format(app_state.message_count, app_state.unknown_count)
    elif msg_text == 'go to sleep':
        logging.warning('Got kill message')
        say("Ok, bye.")
        return 'quit'
    elif ('love' in msg_lower) or ('cute' in msg_lower) or ('best' in msg_lower) or ('awesome' in msg_lower) or ('great' in msg_lower):
        reply = ":blush:"
    elif ('thank you' in msg_lower) or ('thanks' in msg_lower):
        reply = "My pleasure!"
    elif ('tell' in msg_lower and 'joke' in msg_lower) or ('know' in msg_lower and 'jokes' in msg_lower):
        reply_ind = random.choice( range(len(data.jokes)) )
        reply = data.jokes[reply_ind]
    else:
        reply_ind = random.choice( range(len(data.unknown_replies)) )
        reply = data.unknown_replies[reply_ind]
        app_state.unknown_count += 1

    if reply is None:
        say("Somehow I don't know what to say :thinking_face:")
    else:
        say(reply)

    return None

def send_msg(client: WebClient, channel_id: str, msg: str, attach: Optional[List[dict]]=None):
    '''Send a message using the chat postMessage API.'''

    #logging.info('Sending a message to {0}: {1}'.format(channel_id, msg))
    if attach is None:
        client.chat_postMessage(channel=channel_id,
            as_user=True,
            text=msg)
    else:
        client.chat_postMessage(channel=channel_id,
            as_user=True,
            text=msg,
            attachments=attach)

def send_direct_msg(client: WebClient, user_id: str, msg: str):
    '''Send a direct message to a user.'''

    #send_msg(user_id, msg)
    #return

    im = client.im_open(user=user_id)

    try:
        if not 'ok' in im or not im['ok']:
            logging.warning('im open failed')
            return
    except:
        logging.warning('bad im return value: {0}'.format(im))
        return

    #logging.info('opened IM {0}'.format(im))

    im_channel = im['channel']['id']

    send_msg(client, im_channel, msg)

def welcome_msg(client: WebClient, user_id: str, from_user_id: Optional[str]=None):
    '''Send a welcome message to a user'''

    logging.info('Sending welcome message from {0} to {1}'.format(from_user_id,user_id))
    user_info = client.users_info(user=user_id)

    try:
        if not 'ok' in user_info or not user_info['ok']:
            logging.warning('Error getting user info')
            return
    except:
        logging.warning("user_info wasn't a dict: {0}".format(user_info))
        return

    #logging.info('Got user info {0}'.format(user_info))

    user_name = user_info['user']['name']

    welcome = 'Hello ' + user_name + "!\n"

    if from_user_id is None:
        welcome += "I haven't seen you here before, so let me introduce myself.\n"
    else:
        welcome += "<@{0}> asked me to welcome you again.\n".format(from_user_id)

    welcome += "My name is yarnbot, and I'm here to help. You can talk to me in "
    welcome += "this direct message, or by starting a message with '@yarnbot'\n"
    welcome += "Say 'help' to get a list of things I can do."

    send_direct_msg(client, user_id, welcome)

@app.event('team_join')
def welcome_user(event: Event, client: WebClient):
    '''Look at team joins and determine if a welcome is in order'''

    if event is None:
        logging.warning('Got null team join event')
        return

    user = event['user']

    if 'is_bot' in user and user['is_bot']:
        return

    if user['id'] not in app_state.known_users:
        app_state.known_users.append(user['id'])
        save_userdb()
        logging.info('Sending welcome message')
        welcome_msg(client, user['id'])


def load_userdb():
    '''Load the known users list'''

    try:
        userdb_file = open(USERDB_FILENAME, 'rb')
    except:
        userdb_file = open(USERDB_FILENAME, 'wb')
        pickle.dump(app_state.known_users, userdb_file)
        userdb_file.close()
        return

    try:
        app_state.nown_users = pickle.load(userdb_file)
    except:
        logging.error('Malformed userdb file')

    userdb_file.close()

def save_userdb():
    '''Save the known users list'''

    try:
        userdb_file = open(USERDB_FILENAME, 'wb')
    except:
        logging.error("Couldn't write userdb file")
        return

    pickle.dump(app_state.known_users, userdb_file)

    userdb_file.close()


def main(app: App):
    '''Start yarnbot.'''

    logging.basicConfig(filename='yarnbot.log',level=logging.INFO)

    app_state.start_time = time.time()

    auth_info = app.client.auth_test()

    my_user_id = auth_info['user_id']

    logging.info('My user id is {0}'.format(my_user_id))

    my_user = '<@' + my_user_id + '>'
    app_state.bot_user_id = my_user_id
    app_state.bot_user_ref = my_user
    app_state.known_users = [my_user_id]

    load_userdb()

    app.start()

if __name__ == '__main__':
    main(app)

