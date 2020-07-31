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

def calc_sts(data, msg):
    return (data['gauge']/4.)*(data['meas']+data['ease'])

def calc_gauge(data, msg):
    return 4.0*float(data['stitches'])/(data['meas']+data['ease'])

def calc_ease(data, msg):
    return float(data['stitches'])/(data['gauge']/4.) - data['meas']

class EaseConversation:

    def __init__(self):
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
            'answer_stitches': State('answer_stitches', 'Your row length (or cast on) should be {gauge}/4*({meas} + {ease}) = {stitches:.0f} sts', {'stitches':calc_sts}),
            'answer_gauge': State('answer_gauge', 'Your gauge should be 4*{stitches}/({meas} + {ease}) = {gauge:.0f} sts/4 in.', {'gauge':calc_gauge}),
            'answer_ease': State('answer_ease', 'Your ease is {stitches}/({gauge}/4) - {meas} = {ease:.1f} in.', {'ease':calc_ease})
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

        self.data = dict()

        self.current_state = self.states['init']
        self.state_pending = False

    def step(self, input_msg=None):

        if self.current_state.terminal:
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

class State:

    def __init__(self, label, msg=None, extract_dict=None):
        self.label = label
        self.msg = msg
        self.extract_dict = extract_dict
        self.trans = []

        self.terminal = True

        if self.extract_dict is None:
            self.extract_dict = dict()
    
    def set_message(self, msg):
        self.msg = msg

    def add_trans(self, to_state, accept_fn):
        self.trans.append( {'state':to_state, 'accept':accept_fn} )
        self.terminal = False
    
    def extract(self, data, resp):
        
        extracted_data = dict()
        for key,fn in self.extract_dict.items():
            extracted_data[key] = fn(data,resp)

        data.update(extracted_data)

    def enter(self, data):
        #print(f'>>>>> Entering {self.label} with {data}')
        if self.terminal:
            self.extract(data,None)
            msg = self.msg.format(**data)
            return (msg,data)

        prompt = self.msg.format(**data)

        #print(f'>>>>> Responding with {prompt}')
        return (prompt,data)

    def process(self, resp, data):

        #print(f'***** Processing {self.label} with {resp}')
        if resp is None:
            return data

        self.extract(data,resp)

        #print(f'***** Extracted {data}')
        return data

    def exit(self, resp):
        #print(f'<<<<< Exiting {self.label} with {resp}')
        if resp is None:
            return self

        accepted = [ t['state'] for t in self.trans if t['accept'](resp) ]

        if len(accepted) != 1:
            return None

        state = accepted[0]
        #print(f'<<<<< Transition to {state.label}')
        return state

