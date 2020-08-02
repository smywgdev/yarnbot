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

import re


# Accept functions
def accept_string(s):
    return lambda m: s.lower() in m.lower()

def accept_any_strings(*ss):
    return lambda m: any([ s.lower() in m.lower() for s in ss])

def accept_all_strings(*ss):
    return lambda m: all([ s.lower() in m.lower() for s in ss])

def accept():
    return lambda _: True

# Extract functions
def extract_integer(data, msg):
    result = re.search('(-?[0-9]+)', msg)

    if result is not None:
        return int(result.group(0))

def extract_numeric(data, msg):
    result = re.search('(-?[0-9]+\.?[0-9]*|[0-9]*\.?[0-9]+)', msg)

    if result is not None:
        return float(result.group(0))

class State(object):
    '''
    A single state within a state machine.
    '''

    def __init__(self, label, msg=None, extract_dict=None):
        '''
        Parameters:
            label: State name
            msg: Message to emit upon entering
            extract_dict: dictionary of extraction functions, keyed by
                how they should show up in the conversation data dictionary
        '''
        self.label = label
        self.msg = msg
        self.extract_dict = extract_dict
        self.trans = []

        self.terminal = True

        if self.extract_dict is None:
            self.extract_dict = dict()
    
    def set_message(self, msg):
        '''
        The emit message can be altered, or set if not set during state construction.
        '''
        self.msg = msg

    def add_trans(self, to_state, accept_fn):
        '''
        Create a transition from this state to another.

        Parameters:
            to_state: Destination state object
            accept_fn: Function that accepts a string and returns True
                if this transition should be taken.
        '''
        self.trans.append( {'state':to_state, 'accept':accept_fn} )
        self.terminal = False
    
    def extract(self, data, resp):
        '''
        Given response text, extract data from it and update the provided
        data dictionary.

        Parameters:
            Data: dictionary containing conversation data
            resp: Response text to emitted state message
        '''
        extracted_data = dict()
        for key,fn in self.extract_dict.items():
            extracted_data[key] = fn(data,resp)

        data.update(extracted_data)

    def enter(self, data):
        '''
        Enter a state. Upon entering, the state message is emitted.

        Parameters:
            data: Dictionary containing conversation data

        Returns: tuple containing emitted message and potentially updated data
            (updated in the cases that the state is terminal)
        '''
        #print(f'>>>>> Entering {self.label} with {data}')
        if self.terminal:
            self.extract(data,None)
            msg = self.msg.format(**data)
            return (msg,data)

        prompt = self.msg.format(**data)

        #print(f'>>>>> Responding with {prompt}')
        return (prompt,data)

    def process(self, resp, data):
        '''
        Process the response message.

        Parameters:
            resp: Response string
            data: Dictionary containing conversation data

        Returns: Updated data
        '''
        #print(f'***** Processing {self.label} with {resp}')
        if resp is None:
            return data

        self.extract(data,resp)

        #print(f'***** Extracted {data}')
        return data

    def exit(self, resp):
        '''
        Given response text, choose next state.

        Parameters:
            resp: Response text

        Returns: Next state
        '''
        #print(f'<<<<< Exiting {self.label} with {resp}')
        if resp is None:
            return self

        accepted = [ t['state'] for t in self.trans if t['accept'](resp) ]

        if len(accepted) != 1:
            return None

        state = accepted[0]
        #print(f'<<<<< Transition to {state.label}')
        return state

class Conversation(object):
    '''
    A conversation is a state machine in which states emit a message upon entering,
    process a response to that message, and then choose an appropriate next state.

    To define the state machine for a conversation, provide a dictionary of states
    in `self.state` containing State objects, with one special state called 'init'.
    State transitions are provided using the `State.add_trans` method. See `State`
    for more details. For instance:

    self.states = {'init':State('init','Welcome to this state machine'},
                   'A',State('A','This is state A, enter a number',{'num':extract_numeric})}
                   'end',State('end','You said {num}. Bye.')}
    self.states['init'].add_trans(self.states['A'],accept())
    self.states['A'].add_trans(self.states['end'],accept())

    Running this state machine will first print the welcome message, transition to
    'A', extract a number from response text, then transition to end. When finished,
    `self.data` will contain a value for the key 'num'. Any enter message can contain
    references to `self.data` as if being passed to `str.format` (which it is).
    '''

    def __init__(self, name):
        self.name = name
        self.states = {'init': State('init', 'Subclass to have a real conversation')}
        self.current_state = self.states['init']
        self.data = dict()

    def step(self, input_msg=None):
        '''
        Run the machine to the next sttate. `input_msg` is passed to both
        `State.process` and `State.exit`.

        Returns: None if the current state is None or terminal, otherwise
            a (String,Bool) pair containing an output message and whether
            the state is terminal.
        '''

        if self.current_state is None or self.current_state.terminal:
            return None

        self.data = self.current_state.process(input_msg, self.data)

        last_state = self.current_state
        self.current_state = self.current_state.exit(input_msg)

        extra_msg = ''
        if self.current_state is None:
            self.current_state = last_state
            extra_msg = "Sorry, I didn't understand that. "

        (output_msg,self.data) = self.current_state.enter(self.data)

        return (extra_msg+output_msg, self.current_state.terminal)

class EaseConversation(Conversation):
    '''
    Have a conversation about ease, gauge, and number of stitches, based
    on variations of the formula:

        ease = stitches/(gauge/4-measurement)

    Depending on the conversation, the result can be any of ease, gauge,
    or number of stitches.

    The conversation data dictionary (depending on the conversation) contains keys:
    - gauge
    - meas
    - ease
    - stitches
    '''

    # Ease calculations
    @staticmethod
    def calc_sts(data, msg):
        '''
        Calculate number of stitches using values for gauge, pattern measurement and ease.
        sts = (gauge/4)*(meas+ease)
        '''
        return (data['gauge']/4.)*(data['meas']+data['ease'])

    @staticmethod
    def calc_gauge(data, msg):
        '''
        Calculate gauge using values for stitches, pattern measurement and ease.
        gauge = (4*sts)/(meas+ease)
        '''
        return 4.0*float(data['stitches'])/(data['meas']+data['ease'])

    @staticmethod
    def calc_ease(data, msg):
        '''
        Calculate ease using values for stitches, pattern measurement and gauge.
        ease = sts/(gauge/4-meas)
        '''
        return float(data['stitches'])/(data['gauge']/4.) - data['meas']

    def __init__(self):
        super(EaseConversation,self).__init__('ease')

        self.states = {
            'init': State('init', 'Do you have your ease or want to find it?'),
            'have': State('have', 'Great, what is it in inches?', {'ease':extract_numeric}),
            'got_ease': State('got_ease', 'Are you interested in figuring out gauge or number of stitches?'),
            'want_gauge': State('want_gauge', 'How many stitches are in the row with that ease?', {'stitches':extract_integer}),
            'want_sts': State('want_sts', 'What is your gauge in stitches per 4 inches?', {'gauge':extract_integer}),
            'want': State('want', "Ok, we'll need to know gauge, number of stitches, and pattern measurement. Let's start with gauge, how many stitches per 4 inches?", {'gauge':extract_integer}),
            'need_sts': State('need_stitches', 'How many stitches are in the row you need ease for?', {'stitches':extract_integer}),
            'need_meas_sts': State('need_meas_sts', 'What is the measurement according to the pattern?', {'meas':extract_numeric}),
            'need_meas': State('need_meas', 'Lastly, what is the measurement according to the pattern?', {'meas':extract_numeric}),
            'need_gauge_meas': State('need_gauge_meas', 'What is the measurement according to the pattern?', {'meas':extract_numeric}),
            'answer_stitches': State('answer_stitches', 'Your row length (or cast on) should be {gauge}/4*({meas} + {ease}) = {stitches:.0f} sts', {'stitches':EaseConversation.calc_sts}),
            'answer_gauge': State('answer_gauge', 'Your gauge should be 4*{stitches}/({meas} + {ease}) = {gauge:.0f} sts/4 in.', {'gauge':EaseConversation.calc_gauge}),
            'answer_ease': State('answer_ease', 'Your ease is {stitches}/({gauge}/4) - {meas} = {ease:.1f} in.', {'ease':EaseConversation.calc_ease})
            }

        self.states['init'].add_trans(self.states['have'], accept_string('have'))
        self.states['init'].add_trans(self.states['want'], accept_any_strings('want','find'))
        self.states['have'].add_trans(self.states['got_ease'], accept())
        self.states['got_ease'].add_trans(self.states['want_gauge'], accept_string('gauge'))
        self.states['got_ease'].add_trans(self.states['want_sts'], accept_string('stitches'))
        self.states['want'].add_trans(self.states['need_sts'], accept())
        self.states['need_sts'].add_trans(self.states['need_meas'], accept())
        self.states['need_meas'].add_trans(self.states['answer_ease'], accept())
        self.states['want_gauge'].add_trans(self.states['need_gauge_meas'], accept())
        self.states['want_sts'].add_trans(self.states['need_meas_sts'], accept())
        self.states['need_meas_sts'].add_trans(self.states['answer_stitches'], accept())
        self.states['need_gauge_meas'].add_trans(self.states['answer_gauge'], accept())

        self.current_state = self.states['init']


