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

from __future__ import division

import sys
import time
import random
import pickle
import re
import json
import requests
from slackclient import SlackClient
import logging

# Set you bot user ID here
MY_USER_ID = 'bot_user_id'

MY_USER = '<@' + MY_USER_ID + '>'
USERDB_FILENAME = 'known_users.pkl'

VERSION = '1.7.0'

# Ravelry auth info. Set from environment.
RAV_ACC_KEY = ''
RAV_SEC_KEY = ''

known_users = [MY_USER_ID]
reconnect_count = 0
message_count = 0
unknown_count = 0
event_count = 0

unknown_replies = ["I'm not sure what you mean.",
		   "I'm sorry, I don't know that.",
		   "I'm just a sheep.",
		   "I know a lot about other things that aren't that thing.",
		   "Sheep don't understand all of the things yet.",
		   ":thinking_face:",
		   ":confused:",
		   ":persevere:"]

acronyms = {
	'pat': {'desc': 'pattern', 'url': None},
	'pats': {'desc': 'patterns', 'url': None},
	'patt': {'desc': 'pattern', 'url': None},
	'pm': {'desc': 'place marker', 'url': None},
	'pop': {'desc': 'popcorn', 'url': None},
	'p2tog': {'desc': 'purl 2 stitches together', 'url': 'http://www.vogueknitting.com/pattern_help/how-to/beyond_the_basics/decreases/k2tog'},
	'psso': {'desc': 'pass slipped stitch over', 'url': 'http://newstitchaday.com/pass-slipped-stitch-over-decrease/'},
	'pwise': {'desc': 'purlwise', 'url': None},
	'beg': {'desc': 'begin/beginning', 'url': None},
	'rem': {'desc': 'remain/remaining', 'url': None},
	'bet': {'desc': 'between', 'url': None},
	'rep': {'desc': 'repeat(s)', 'url': None},
	'bo': {'desc': 'bind off', 'url': 'http://www.vogueknitting.com/pattern_help/how-to/learn_to_knit/binding_off'},
	'ca': {'desc': 'color A', 'url': None},
	'rh': {'desc': 'right hand', 'url': None},
	'cb': {'desc': 'color B ', 'url': None},
	'rnd': {'desc': 'round', 'url': None},
	'rnds': {'desc': 'rounds', 'url': None},
	'cc': {'desc': 'contrasting color ', 'url': None},
	'rs': {'desc': 'right side ', 'url': None},
	'sk': {'desc': 'skip', 'url': None},
	'cn': {'desc': 'cable needle', 'url': None},
	'skp': {'desc': 'slip, knit, pass stitch over; one stitch decreased', 'url': 'http://www.vogueknitting.com/pattern_help/how-to/beyond_the_basics/decreases/skp'},
	'co': {'desc': 'cast on', 'url': 'http://www.vogueknitting.com/pattern_help/how-to/learn_to_knit/first_stitches'},
	'sk2p': {'desc': 'slip 1, knit 2 together, pass slip stitch over the knit 2 together; 2 stitches have been decreased', 'url': 'http://newstitchaday.com/slip-knit-two-pass-double-decrease/'},
	'cont': {'desc': 'continue ', 'url': None},
	'sl': {'desc': 'slip ', 'url': None},
	'dec': {'desc': 'decrease/decreases/decreasing', 'url': 'http://www.vogueknitting.com/pattern_help/how-to/beyond_the_basics/decreases'},
	'sl1k': {'desc': 'slip 1 knitwise', 'url': 'https://www.youtube.com/watch?v=_Wh8kmdqfcw'},
	'dpn': {'desc': 'double pointed needle(s)', 'url': None},
	'sl1p': {'desc': 'slip 1 purlwise', 'url': 'https://www.youtube.com/watch?v=6EX_KbVknP0'},
	'fl': {'desc': 'front loop(s)', 'url': None},
	'sl': {'desc': 'st slip stitch(es)', 'url': None},
	'foll': {'desc': 'follow/follows/following', 'url': None},
	'ss': {'desc': 'slip stitch', 'url': None},
	'ssk': {'desc': 'slip, slip, knit these 2 stiches together; decrease', 'url': 'http://www.vogueknitting.com/pattern_help/how-to/beyond_the_basics/decreases/ssk'},
	'inc': {'desc': 'increase/increases/increasing', 'url': 'http://www.vogueknitting.com/pattern_help/how-to/beyond_the_basics/increases'},
	'sssk': {'desc': 'slip, slip, slip, knit 3 stitches together', 'url': 'http://newstitchaday.com/slip-slip-slip-knit-double-decrease/'},
	'k': {'desc': 'knit', 'url': 'http://www.vogueknitting.com/pattern_help/how-to/learn_to_knit/the_knit_stitch'},
	'st': {'desc': 'stitch', 'url': None},
	'sts': {'desc': 'stitches', 'url': None},
	'k2tog': {'desc': 'knit 2 stitches together', 'url': 'http://www.vogueknitting.com/pattern_help/how-to/beyond_the_basics/decreases/k2tog'},
	'st': {'desc': 'st stockinette stitch/stocking stitch', 'url': None},
	'kwise': {'desc': 'knitwise', 'url': None},
	'tbl': {'desc': 'through back loop', 'url': 'http://newstitchaday.com/k-tbl-knit-through-back-loop/'},
	'lh': {'desc': 'left hand', 'url': None},
	'tog': {'desc': 'together', 'url': None},
	'lp': {'desc': 'loop', 'url': None},
	'lps': {'desc': 'loops', 'url': None},
	'ws': {'desc': 'wrong side', 'url': None},
	'wyib': {'desc': 'with yarn in back', 'url': None},
	'm1': {'desc': 'make one stitch', 'url': 'http://www.vogueknitting.com/pattern_help/how-to/beyond_the_basics/increases/make_one_increase'},
	'm1r': {'desc': 'make one stitch right', 'url': 'http://newstitchaday.com/m1r-make-one-right-increase-knitting/'},
	'm1l': {'desc': 'make one stitch left', 'url': 'http://newstitchaday.com/m1l-make-one-left-increase-knitting/'},
	'wyif': {'desc': 'with yarn in front', 'url': None},
	'mc': {'desc': 'main color', 'url': None},
	'yfwd': {'desc': 'yarn forward', 'url': None},
	'yo': {'desc': 'yarn over', 'url': None},
	'oz': {'desc': 'ounce(s)', 'url': None},
	'yrn': {'desc': 'yarn around needle', 'url': None},
	'p': {'desc': 'purl', 'url': 'http://www.vogueknitting.com/pattern_help/how-to/learn_to_knit/the_purl_stitch'},
	'yon': {'desc': 'yarn over needle', 'url': None}}

yarn_weights = {
	'cobweb':          {'ply': 1, 'wpi': '??', 'gauge': '??', 'number': 0},
	'lace':            {'ply': 2, 'wpi': '??', 'gauge': '32-34', 'number': 0},
	'light fingering': {'ply': 3, 'wpi': '??', 'gauge': '32', 'number': 0},
	'fingering':       {'ply': 4, 'wpi': '14', 'gauge': '28', 'number': 1},
	'sport':           {'ply': 5, 'wpi': '12', 'gauge': '24-26', 'number': 2},
	'dk':              {'ply': 8, 'wpi': '11', 'gauge': '22', 'number': 3},
	'worsted':         {'ply': 10, 'wpi': '9', 'gauge': '20', 'number': 4},
	'aran':            {'ply': 10, 'wpi': '8', 'gauge': '18', 'number': 4},
	'bulky':           {'ply': 12, 'wpi': '7', 'gauge': '14-15', 'number': 5},
	'super bulky':     {'ply': '??', 'wpi': '5-6', 'gauge': '7-12', 'number': 6},
	'jumbo':           {'ply': '??', 'wpi': '0-4', 'gauge': '0-6', 'number': 7}
	}

yarn_fibers = [
	'acrylic',
	'alpaca',
	'angora',
	'bamboo',
	'bison',
	'camel',
	'cashmere',
	'cotton',
	'hemp',
	'linen',
	'llama',
	'merino',
	'metallic',
	'microfiber',
	'mohair',
	'nylon',
	'other',
	'plant-fiber',
	'polyester',
	'qiviut',
	'rayon',
	'silk',
	'soy',
	'tencel',
	'wool',
	'yak'
	]

needles_by_us = {
	'0': {'metric': '2.0', 'uk': '14', 'crochet': '-'},
	'1': {'metric': '2.25', 'uk': '13', 'crochet': 'B'},
	'2': {'metric': '2.75', 'uk': '12', 'crochet': 'C'},
	'3': {'metric': '3.0', 'uk': '11', 'crochet': '-'},
	'3': {'metric': '3.25', 'uk': '10', 'crochet': 'D'},
	'4': {'metric': '3.5', 'uk': '9', 'crochet': 'E'},
	'5': {'metric': '3.75', 'uk': '9', 'crochet': 'F'},
	'6': {'metric': '4.0', 'uk': '8', 'crochet': 'G'},
	'7': {'metric': '4.5', 'uk': '7', 'crochet': '-'},
	'8': {'metric': '5.0', 'uk': '6', 'crochet': 'H'},
	'9': {'metric': '5.5', 'uk': '5', 'crochet': 'I'},
	'10': {'metric': '6.0', 'uk': '4', 'crochet': 'J'},
	'10.5': {'metric': '6.5', 'uk': '3', 'crochet': 'K'},
	'10 1/2': {'metric': '6.5', 'uk': '3', 'crochet': 'K'},
	'11': {'metric': '8.0', 'uk': '0', 'crochet': 'L'},
	'13': {'metric': '9.0', 'uk': '00', 'crochet': '-'},
	'15': {'metric': '10.0', 'uk': '000', 'crochet': '-'},
	'17': {'metric': '12.0', 'uk': '-', 'crochet': '-'},
	'19': {'metric': '15.0', 'uk': '-', 'crochet': '-'},
	'35': {'metric': '20.0', 'uk': '-', 'crochet': '-'},
	'50': {'metric': '50.0', 'uk': '-', 'crochet': '-'},
	}
needles_by_metric = {
	'2.00': {'us': '0', 'uk': '14', 'crochet': '-'},
	'2.25': {'us': '1', 'uk': '13', 'crochet': 'B'},
	'2.50': {'us': '-', 'uk': '12', 'crochet': '-'},
	'2.75': {'us': '2', 'uk': '12', 'crochet': 'C'},
	'3.00': {'us': '3', 'uk': '11', 'crochet': '-'},
	'3.25': {'us': '3', 'uk': '10', 'crochet': 'D'},
	'3.50': {'us': '4', 'uk': '9', 'crochet': 'E'},
	'3.75': {'us': '5', 'uk': '9', 'crochet': 'F'},
	'4.00': {'us': '6', 'uk': '8', 'crochet': 'G'},
	'4.50': {'us': '7', 'uk': '7', 'crochet': '-'},
	'5.00': {'us': '8', 'uk': '6', 'crochet': 'H'},
	'5.50': {'us': '9', 'uk': '5', 'crochet': 'I'},
	'6.00': {'us': '10', 'uk': '4', 'crochet': 'J'},
	'6.50': {'us': '10.5', 'uk': '3', 'crochet': 'K'},
	'7.00': {'us': '-', 'uk': '2', 'crochet': '-'},
	'7.50': {'us': '-', 'uk': '1', 'crochet': '-'},
	'8.00': {'us': '11', 'uk': '0', 'crochet': 'L'},
	'9.00': {'us': '13', 'uk': '00', 'crochet': '-'},
	'10.00': {'us': '15', 'uk': '000', 'crochet': '-'},
	'12.00': {'us': '17', 'uk': '-', 'crochet': '-'},
	'15.00': {'us': '19', 'uk': '-', 'crochet': '-'},
	'20.00': {'us': '35', 'uk': '-', 'crochet': '-'},
	'50.00': {'us': '50', 'uk': '-', 'crochet': '-'},
	}
needles_by_crochet = {
	'B': {'us': '1', 'uk': '13', 'metric': '2.25'},
	'C': {'us': '2', 'uk': '12', 'metric': '2.75'},
	'D': {'us': '3', 'uk': '10', 'metric': '3.25'},
	'E': {'us': '4', 'uk': '9', 'metric': '3.5'},
	'F': {'us': '5', 'uk': '9', 'metric': '3.75'},
	'G': {'us': '6', 'uk': '8', 'metric': '4.0'},
	'H': {'us': '8', 'uk': '6', 'metric': '5.0'},
	'I': {'us': '9', 'uk': '5', 'metric': '5.5'},
	'J': {'us': '10', 'uk': '4', 'metric': '6.0'},
	'K': {'us': '10.5', 'uk': '3', 'metric': '6.5'},
	'L': {'us': '11', 'uk': '0', 'metric': '8.0'}
	}
needles_by_uk = {
	'14': {'us': '0', 'crochet': '-', 'metric': '2.0'},
	'13': {'us': '1', 'crochet': 'B', 'metric': '2.25'},
	'12': {'us': '-', 'crochet': '-', 'metric': '2.5'},
	'12': {'us': '2', 'crochet': 'C', 'metric': '2.75'},
	'11': {'us': '3', 'crochet': '-', 'metric': '3.0'},
	'10': {'us': '3', 'crochet': 'D', 'metric': '3.25'},
	'9': {'us': '4', 'crochet': 'E', 'metric': '3.5'},
	'9': {'us': '5', 'crochet': 'F', 'metric': '3.75'},
	'8': {'us': '6', 'crochet': 'G', 'metric': '4.0'},
	'7': {'us': '7', 'crochet': '-', 'metric': '4.5'},
	'6': {'us': '8', 'crochet': 'H', 'metric': '5.0'},
	'5': {'us': '9', 'crochet': 'I', 'metric': '5.5'},
	'4': {'us': '10', 'crochet': 'J', 'metric': '6.0'},
	'3': {'us': '10.5', 'crochet': 'K', 'metric': '6.5'},
	'2': {'us': '-', 'crochet': '-', 'metric': '7.0'},
	'1': {'us': '-', 'crochet': '-', 'metric': '7.5'},
	'0': {'us': '11', 'crochet': 'L', 'metric': '8.0'},
	'00': {'us': '13', 'crochet': '-', 'metric': '9.0'},
	'000': {'us': '15', 'crochet': '-', 'metric': '10.0'},
	}

jokes = [
	"Why did the pig farmer give up knitting?\n\nHe didn't want to cast his purls before swine.",
	"Did you hear what happened to the cat who ate a ball of yarn?\n\nShe had mittens.",
	"So this lady was driving down the highway crocheting as she drove. A highway patrolman noticed her and began pursuit. He drove up next to her car, rolled down his window and said, 'Pull over!' She replied, 'No, it's a scarf!'",
	"How do you make knitted jewelry?\n\nWith purls.",
	"Why are Christmas trees bad at knitting?\n\nBecause they keep dropping their needles",
	"What did the knitted cap say to the afghan?\n\nYou stay here, I'll go on a head."]

'''
mm	UK	US	crochet
2.0 mm	14	0	
2.25 mm	13	1	B
2.5 mm	12	-	
2.75 mm	12	2	C
3.0 mm	11	3	
3.25 mm	10	3	D
3.5 mm	9	4	E
3.75 mm	9	5	F
4.0 mm	8	6	G
4.5 mm	7	7	
5.0 mm	6	8	H
5.5 mm	5	9	I
6.0 mm	4	10	J
6.5 mm	3	10 1/2	K
7.0 mm	2	-	
7.5 mm	1	-	
8.0 mm	0	11	L
9.0 mm	00	13	
10.0 mm	000	15	
12.0 mm		17	
15.0 mm		19	
20.0 mm		35	
50.0 mm		50	
'''

def yarn_distance(yarn1, yarn2):

	mass1 = yarn1['grams']
	mass2 = yarn2['grams']
	yards1 = yarn1['yardage']
	yards2 = yarn2['yardage']
	wpi1 = yarn1['wpi']
	wpi2 = yarn1['wpi']
	min_gauge1 = yarn1['min_gauge']
	min_gauge2 = yarn2['min_gauge']
	max_gauge1 = yarn1['max_gauge']
	max_gauge2 = yarn2['max_gauge']
	gauge_div1 = yarn1['gauge_divisor']
	gauge_div2 = yarn2['gauge_divisor']


	# Density
	if mass1 != None and yards1 != None:
		density1 = float(mass1)/float(yards1)
	else:
		density1 = None

	if mass2 != None and yards2 != None:
		density2 = float(mass2)/float(yards2)
	else:
		density2 = None

	# Gauge
	if gauge_div1 != None and min_gauge1 != None:
		min_gauge_norm1 = min_gauge1/gauge_div1
	else:
		min_gauge_norm1 = None
	if gauge_div1 != None and max_gauge1 != None:
		max_gauge_norm1 = max_gauge1/gauge_div1
	else:
		max_gauge_norm1 = None

	if gauge_div2 != None and min_gauge2 != None:
		min_gauge_norm2 = min_gauge2/gauge_div2
	else:
		min_gauge_norm2 = None
	if gauge_div2 != None and max_gauge2 != None:
		max_gauge_norm2 = max_gauge2/gauge_div2
	else:
		max_gauge_norm2 = None


	# Distance measures

	dist = lambda x,y: float(abs(x-y))/(x+y)
	d = 0.

	if density1 != None and density2 != None:
		d += dist(density1,density2)
	else:
		d += 0.5

	if wpi1 != None and wpi2 != None:
		d += dist(wpi1,wpi2)
	else:
		d += 0.5

	if min_gauge_norm1 != None and min_gauge_norm2 != None:
		d += dist(min_gauge_norm1,min_gauge_norm1)
	else:
		d += 0.5
	if max_gauge_norm1 != None and max_gauge_norm2 != None:
		d += dist(max_gauge_norm1,max_gauge_norm1)
	else:
		d += 0.5

	return d

def ravelry_api(api_call, parms):

	req = requests.get('https://api.ravelry.com/' + api_call, auth=(RAV_ACC_KEY,RAV_SEC_KEY), params=parms)

	return req.json()

def ravelry_api_yarn(rav_cmd, page_size=5):


	filtered_words = ['or','and','pattern',
		'patterns','with','using',
		'weight','weights','color']
	for w in filtered_words:
		if w in rav_cmd:
			rav_cmd.remove(w)

	parms = {'photo':'yes', 'page_size':str(page_size), 'sort':'projects'}
	msg = 'Yarn search results for:'
	
	filter_weight = []
	for w in yarn_weights.keys():
		s = w.lower().replace(' ','-')
		if s in rav_cmd:
			filter_weight.append(s)
			rav_cmd.remove(s)

	filter_fiber = []
	for f in yarn_fibers:
		if f in rav_cmd:
			filter_fiber.append(f)
			rav_cmd.remove(f)


	if len(filter_weight) > 0:
		parms.update({'weight': '|'.join(filter_weight)})
		msg += ' {0} weight'.format( ' or '.join(filter_weight) )

	if len(filter_fiber) > 0:
		parms.update({'fiber': '+'.join(filter_fiber)})
		msg += ' with {0} fiber'.format( ' and '.join(filter_fiber) )

	parms.update({'query':' '.join(rav_cmd)})
	msg += ' containing "{0}"'.format(' '.join(rav_cmd))

	rav_result = ravelry_api('/yarns/search.json', parms)
	
	return (rav_result, msg, parms)


def ravelry_yarn(rav_cmd):

	(rav_result, msg, parms) = ravelry_api_yarn(rav_cmd)

	if rav_result['paginator']['results'] == 0:
		return (None,None)

	attachments = []
	for info in rav_result['yarns']:
		
		mach_wash = info['machine_washable']
		if mach_wash == None or not mach_wash:
			mach_wash = 'No'
		else:
			mach_wash = 'Yes'

		organic = info['organic']
		if organic == None or not organic:
			organic = 'No'
		else:
			organic = 'Yes'

		if info.has_key('yarn_weight'):
			description = info['yarn_weight']['name']
		else:
			description = 'roving?'

		if info['gauge_divisor'] != None:
			gauge_range = []
			if info['min_gauge'] != None:
				gauge_range.append(str(info['min_gauge']))
			if info['max_gauge'] != None:
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

	attach_json = json.dumps( attachments )

	return (msg, attach_json)

def ravelry_pattern(rav_cmd):

	filtered_words = ['or','and','pattern',
		'patterns','with','using','yarn',
		'weight','weights','color']
	for w in filtered_words:
		if w in rav_cmd:
			rav_cmd.remove(w)

	parms = {'photo':'yes', 'page_size':'5', 'sort':'projects'}
	msg = 'Pattern search results for:'
	
	filter_free = 'free' in rav_cmd
	if filter_free:
		rav_cmd.remove('free')
		msg += ' free'

	filter_craft = []
	if 'knit' in rav_cmd or 'knitting' in rav_cmd:
		filter_craft.append('knitting')
		try:
			rav_cmd.remove('knit')
			rav_cmd.remove('knitting')
		except:
			pass
	if 'crochet' in rav_cmd:
		filter_craft.append('crochet')
		rav_cmd.remove('crochet')
	
	filter_weight = []
	for w in yarn_weights.keys():
		s = w.lower().replace(' ','-')
		if s in rav_cmd:
			filter_weight.append(s)
			rav_cmd.remove(s)

	if filter_free:
		parms.update({'availability':'free'})
	if len(filter_craft) > 0:
		parms.update({'craft': '|'.join(filter_craft)})
		msg += ' {0}'.format( ' or '.join(filter_craft) )

	if len(filter_weight) > 0:
		parms.update({'weight': '|'.join(filter_weight)})
		msg += ' with {0} yarn'.format( ' or '.join(filter_weight) )

	parms.update({'query':' '.join(rav_cmd)})
	msg += ' containing "{0}"'.format(' '.join(rav_cmd))

	search_query = '&'.join([ k + '=' + requests.utils.quote(v) for (k,v) in parms.items() if k != 'page_size'])
	search_url = 'http://www.ravelry.com/patterns/search#' + search_query

	msg += '\n(<{0}|search on ravelry>)'.format(search_url)


	rav_result = ravelry_api('/patterns/search.json', parms)

	if rav_result['paginator']['results'] == 0:
		return (None,None)

	attachments = []
	for pat in rav_result['patterns']:
		
		attachment = dict()
		attachment['fallback'] = pat['name']
		attachment['color'] = '#36a64f'
		attachment['author_name'] = pat['designer']['name']
		attachment['title'] = pat['name']
		attachment['title_link'] = 'https://www.ravelry.com/patterns/library/' + pat['permalink']
		attachment['image_url'] = pat['first_photo']['square_url']

		attachments.append( attachment )


	attach_json = json.dumps( attachments )

	return (msg,attach_json)


def proc_msg(evt):

	global message_count
	global reconnect_count
	global unknown_count
	global event_count

	reply = None

	if evt.has_key('subtype'):
		return None
	
	user_id = evt['user']
	channel_id = evt['channel']
	msg_text = evt['text']

	if user_id == MY_USER_ID:
		return None
	
	direct_msg = channel_id.startswith('D')

	if ':sheep:' in msg_text:
		reply = "Did someone say :sheep:?"
		sc.api_call("chat.postMessage",
			channel=channel_id,
			as_user=True,
			text=reply)
		return None

	if msg_text.startswith(MY_USER):
		direct_msg = True
		msg_text = msg_text.split('>',1)[1]
		if len(msg_text) <= 0:
			return None
		if not msg_text[0].isalnum():
			msg_text = msg_text[1:].strip()

	if not direct_msg:
		return None

	msg_lower = msg_text.lower()
	msg_stripped = str(msg_lower).translate(None, '.,!?:;')

	if acronyms.has_key(msg_stripped):
		reply = "*{0}* is {1}".format(msg_text, acronyms[msg_stripped]['desc'])
		if acronyms[msg_stripped]['url'] != None:
			reply += "\n<{0}|more info>".format(acronyms[msg_stripped]['url'])
	elif msg_stripped == 'help':
		reply = "I understand:\n"
		reply += "  &lt;7 character abbreviations\n"
		reply += "  Yarn weights\n"
		reply += "  Needle/Hook sizes (say 'US 10', '5mm', 'Crochet L', etc)\n"
		reply += "  Basic arithmetic expressions\n"
		reply += "  *weights*: List all yarn weights\n"
		reply += "  *ravelry favorites* &lt;Ravelry Username&gt;\n"
		reply += "  *ravelry favorites* &lt;Ravelry Username&gt; *tagged* &lt;tag&gt;\n"
		reply += "  *ravelry search* &lt;search terms&gt;: Search patterns\n"
		reply += "  *ravelry yarn* &lt;search terms&gt;: Search yarn\n"
		reply += "  *ravelry yarn similar to* &lt;search terms&gt;: Find similar yarn\n"
		reply += "  *info*: Yarnbot info\n"
		reply += "  *help*: This text"
	elif yarn_weights.has_key(msg_stripped):
		yarn_info = yarn_weights[msg_stripped]
		reply = "*{0}* weight yarn is number {1}, typically {2} stitches per 4 in., {3}-ply, {4} wraps per inch".format(msg_stripped,
		    yarn_info['number'],
		    yarn_info['gauge'],
		    yarn_info['ply'],
		    yarn_info['wpi'])
	elif msg_lower.startswith('us '):
		m = re.match('^us ([0-9.]+)', msg_lower)
		if m:
			size = m.groups()[0]
			if needles_by_us.has_key(size):
				reply = "*US size {0}* is {1} mm, UK {2}, Crochet {3}".format(size,
						needles_by_us[size]['metric'],
						needles_by_us[size]['uk'],
						needles_by_us[size]['crochet'])
			else:
				reply = "US {0} doesn't seem to be a standard size.".format(size)
	elif msg_lower.startswith('uk '):
		m = re.match('^uk ([0-9.]+)', msg_lower)
		if m:
			size = m.groups()[0]
			if needles_by_uk.has_key(size):
				reply = "*UK size {0}* is {1} mm, US {2}, Crochet {3}".format(size,
						needles_by_uk[size]['metric'],
						needles_by_uk[size]['us'],
						needles_by_uk[size]['crochet'])
			else:
				reply = "UK {0} doesn't seem to be a standard size.".format(size)
	elif re.match('^[0-9.]+ *mm', msg_lower):
		m = re.match('^([0-9.]+) *mm', msg_lower)
		if m:
			size = "{0:.2f}".format(float(m.groups()[0]))
			if needles_by_metric.has_key(size):
				reply = "*{0} mm* needles/hooks are US {1}, UK {2}, Crochet {3}".format(size,
						needles_by_metric[size]['us'],
						needles_by_metric[size]['uk'],
						needles_by_metric[size]['crochet'])
			else:
				reply = "{0} mm doesn't seem to be a standard size.".format(size)
	elif msg_lower.startswith('crochet '):
		m = re.match('^crochet ([a-z])', msg_lower)
		if m:
			size = m.groups()[0].upper()
			if needles_by_crochet.has_key(size):
				reply = "*Crochet {0}* is {1} mm, US {2}, UK {3}".format(size,
						needles_by_crochet[size]['metric'],
						needles_by_crochet[size]['us'],
						needles_by_crochet[size]['uk'])
			else:
				reply = "Crochet {0} doesn't seem to be a standard size.".format(size)
	elif msg_stripped == 'weights':
		reply = "These are all of the yarn weights I know about:\n"
		for w in yarn_weights.keys():
			reply += "  " + w + "\n"

	
	elif re.match('^[0-9+-/*. ()]+$', msg_stripped):
		try:
			reply = '{0}'.format( eval(msg_stripped) )
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
					send_msg(channel_id, reply)
					return None
				elif num_yarns < 1:
					reply = "That yarn description didn't return any results :disappointed:"
					send_msg(channel_id, reply)
					return None

				target_yarn = target_results['yarns'][0]

				detail_results = ravelry_api('yarns/{0}.json'.format(target_yarn['id']), {'id': target_yarn['id']})
				target_yarn_detail = detail_results['yarn']
				target_fibers = [ x['fiber_type']['name'].lower().replace(' ','-') for x in target_yarn_detail['yarn_fibers'] ]

				target_weight = target_yarn_detail['yarn_weight']['name'].lower().replace(' ','-')

				similar_results, msg, parms = ravelry_api_yarn(target_fibers + [target_weight], 50)

				if similar_results['paginator']['results'] < 1:
					reply = 'No results.... somehow'
					send_msg(channel_id, reply)
					return None

				# Sort results by yarn comparison
				
				similar_sorted = sorted(similar_results['yarns'], key=lambda x: yarn_distance(target_yarn, x))
				attachments = []
				for info in similar_sorted[0:5]:
					
					mach_wash = info['machine_washable']
					if mach_wash == None or not mach_wash:
						mach_wash = 'No'
					else:
						mach_wash = 'Yes'

					organic = info['organic']
					if organic == None or not organic:
						organic = 'No'
					else:
						organic = 'Yes'

					description = info['yarn_weight']['name']
					if info['gauge_divisor'] != None:
						gauge_range = []
						if info['min_gauge'] != None:
							gauge_range.append(str(info['min_gauge']))
						if info['max_gauge'] != None:
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

				msg = "Yarn most similar to {0} {1} {2}-weight ({3})".format(target_yarn['yarn_company_name'],target_yarn['name'],target_weight,','.join(target_fibers))
				attach_json = json.dumps( attachments )

				send_msg(channel_id, msg, attach_json)

				return None

			elif rav_cmd[1] == 'yarn':

				(msg, attach) = ravelry_yarn(rav_cmd[2:])

				if msg != None:
					send_msg(channel_id, msg, attach)
				else:
					send_msg(channel_id, ':disappointed:')

				return None


			elif rav_cmd[1] == 'search':
				
				(msg, attach) = ravelry_pattern(rav_cmd[2:])

				if msg != None:
					send_msg(channel_id, msg, attach)
				else:
					send_msg(channel_id, ':disappointed:')

				return None

			if rav_cmd[1] == 'favorites':
				fav_user = rav_cmd[2]
				parms = {'username':fav_user, 'page_size':'5'}
				msg = "Most recent favorites for {0}".format(fav_user)
				if len(rav_cmd) > 3:
					if rav_cmd[3] == 'tagged' and len(rav_cmd) > 4:
						parms.update( {'tag': rav_cmd[4]} )
						msg += ', tagged {0}'.format(rav_cmd[4])
					else:
						query = " ".join(rav_cmd[3:])
						parms.update( {'query': query} )
						msg += ', containing {0}'.format(query) 
				rav_result = ravelry_api('/people/{0}/favorites/list.json'.format(fav_user), parms)

				if rav_result['paginator']['results'] == 0:
					send_msg(channel_id, ':disappointed:')
					return None

				attachments = []
				for fav in rav_result['favorites']:
					
					attachment = dict()
					attachment['fallback'] = fav['favorited']['name']
					attachment['color'] = '#36a64f'
					attachment['author_name'] = fav['favorited']['designer']['name']
					attachment['title'] = fav['favorited']['name']
					attachment['title_link'] = 'https://www.ravelry.com/patterns/library/' + fav['favorited']['permalink']
					attachment['image_url'] = fav['favorited']['first_photo']['square_url']

					attachments.append( attachment )

				attach_json = json.dumps( attachments )

				sc.api_call("chat.postMessage",
					channel=channel_id,
					as_user=True,
					text=msg,
					attachments=attach_json)
				return None

		except Exception as e:
			reply = 'Ravelry command error'
			logging.warn('Ravelry error line {0}: {1}'.format(sys.exc_info()[2].tb_lineno,e.message) )

	elif msg_stripped == 'hello' or msg_stripped == 'hi' or msg_stripped.startswith('hello ') or msg_stripped.startswith('hi '):
		reply = "Hi!"
	elif msg_stripped == 'info':
		reply = "I'm yarnbot {0}, started on {2}.\n".format(VERSION, time.ctime(start_time))
		reply += "I've processed {0} events, {1} messages ({2} unknown), and had to reconnect {3} times.".format(event_count, message_count, unknown_count, reconnect_count)
	elif msg_text == 'go to sleep':
		logging.warn('Got kill message')
		reply = "Ok, bye."
		sc.api_call("chat.postMessage",
			channel=channel_id,
			as_user=True,
			text=reply)
		return 'quit'
	elif ('love' in msg_lower) or ('cute' in msg_lower) or ('best' in msg_lower) or ('awesome' in msg_lower) or ('great' in msg_lower):
		reply = ":blush:"
	elif ('thank you' in msg_lower) or ('thanks' in msg_lower):
		reply = "My pleasure!"
	elif ('tell' in msg_lower and 'joke' in msg_lower) or ('know' in msg_lower and 'jokes' in msg_lower):
		reply_ind = random.choice( range(len(jokes)) );
		reply = jokes[reply_ind]
	else:
		reply_ind = random.choice( range(len(unknown_replies)) );
		reply = unknown_replies[reply_ind]
		unknown_count += 1

	send_msg(channel_id, reply)

	return None

def send_msg(channel_id, msg):

	#logging.info('Sending a message to {0}: {1}'.format(channel_id, msg))
	sc.api_call("chat.postMessage",
		channel=channel_id,
		as_user=True,
		text=msg)

def send_msg(channel_id, msg, attach=None):

	#logging.info('Sending a message to {0}: {1}'.format(channel_id, msg))
	if attach == None:
		sc.api_call("chat.postMessage",
			channel=channel_id,
			as_user=True,
			text=msg)
	else:
		sc.api_call("chat.postMessage",
			channel=channel_id,
			as_user=True,
			text=msg,
			attachments=attach)




def send_direct_msg(user_id, msg):

	#send_msg(user_id, msg)
	#return

	im = sc.api_call('im.open', user=user_id)

	try:
		if not im.has_key('ok') or not im['ok']:
			logging.warn('im open failed')
			return
	except:
		logging.warn('bad im return value: {0}'.format(im))
		return
	
	#logging.info('opened IM {0}'.format(im))
	
	im_channel = im['channel']['id']

	send_msg(im_channel, msg)

def welcome_msg(user_id):

	#logging.info('Sending message to {0}'.format(user_id))
	user_info = sc.api_call('users.info', user=user_id)

	try:
		if not user_info.has_key('ok') or not user_info['ok']:
			logging.warn('Error getting user info')
			return
	except:
		logging.warn("user_info wasn't a dict: {0}".format(user_info))
		return

	#logging.info('Got user info {0}'.format(user_info))

	user_name = user_info['user']['name']

	welcome = 'Hello ' + user_name + "!\n"
	welcome += "I haven't seen you here before, so let me introduce myself.\n"
	welcome += "My name is yarnbot, and I'm here to help. You can talk to me in "
	welcome += "this direct message, or by starting a message with '@yarnbot'\n"
	welcome += "Say 'help' to get a list of things I can do."

	send_direct_msg(user_id, welcome)

def main_loop():

	global reconnect_count
	global message_count
	global event_count

	please_close = False

	while not please_close:
		try:
			evt = sc.rtm_read()
		except:
			logging.warn('Excepting on rtm read')
			while True:
				logging.warn('Trying to reconnect')
				if sc.rtm_connect():
					break
				time.sleep(1)
			reconnect_count += 1
			evt = []

		if len(evt) <= 0:
			time.sleep(1)
			continue

		event_count += 1

		if evt[0].has_key('type'):
			evt_type = evt[0]['type']
		else:
			logging.info("Got no-type event: {0}".format(evt[0]))
			continue

		if evt_type != u'reconnect_url':
			logging.info("Got event {0}".format(evt[0]))

		if evt_type == u'goodbye':
			please_close = True
		elif evt_type == u'message':
			ret = proc_msg(evt[0])
			message_count += 1
			if ret != None:
				if ret == 'quit':
					please_close = True
		elif evt_type == u'presence_change':
			presence = evt[0]['presence']
			user = evt[0]['user']

			#logging.info('I saw a presence change: {0}'.format(evt[0]))
			#logging.info('looking for {0} in known users'.format(user))

			if presence == u'active' and user not in known_users:
				known_users.append(user)
				save_userdb()
				#logging.info('Sending welcome message')
				welcome_msg(user)



	logging.info('Main loop exiting')

def load_userdb():
	global known_users

	try:
		userdb_file = open(USERDB_FILENAME, 'rb')
	except:
		userdb_file = open(USERDB_FILENAME, 'wb')
		pickle.dump(known_users, userdb_file)
		userdb_file.close()
		return

	try:
		known_users = pickle.load(userdb_file)
	except:
		logging.error('Malformed userdb file')
	
	userdb_file.close()

def save_userdb():
	global known_users

	try:
		userdb_file = open(USERDB_FILENAME, 'wb')
	except:
		logging.error("Couldn't write userdb file")
		return

	pickle.dump(known_users, userdb_file)
	
	userdb_file.close()

	


if __name__ == '__main__':
	logging.basicConfig(filename='yarnbot.log',level=logging.INFO)
	
	RAV_ACC_KEY = os.environ.get('RAV_ACC_KEY')
	RAV_SEC_KEY = os.environ.get('RAV_SEC_KEY')

	start_time = time.time()

	load_userdb()

	SLACK_API_KEY = os.environ.get('SLACK_API_KEY')
	sc = SlackClient('SLACK_API_KEY')

	if not sc.rtm_connect():
		logging.error("Couldn't connect to RTM in rtm_connect")
		sys.exit()

	time.sleep(1)

	evt = sc.rtm_read()

	if len(evt) < 1 or evt[0]['type'] != u'hello':
		logging.error("Couldn't connect to RTM (bad reply event {0})".format(evt))
		sc.api_call("chat.postMessage",
			channel="#test",
			as_user=True,
			text="I couldn't connect to RTM :(")
		sys.exit()

	sc.api_call("chat.postMessage",
		channel="#test",
		as_user=True,
		text="Hello, I'm yarnbot. *yawn*")

	main_loop()

	sc.api_call("chat.postMessage",
		channel="#test",
		as_user=True,
		text="I'm disconnecting.")


