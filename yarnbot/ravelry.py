import os
import json
import requests

RAV_ACC_KEY = os.environ.get('RAV_ACC_KEY')
RAV_SEC_KEY = os.environ.get('RAV_SEC_KEY')

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
    msg = u'Yarn search results for:'
    
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
        msg += u' {0} weight'.format( ' or '.join(filter_weight) )

    if len(filter_fiber) > 0:
        parms.update({'fiber': '+'.join(filter_fiber)})
        msg += u' with {0} fiber'.format( ' and '.join(filter_fiber) )

    parms.update({'query':' '.join(rav_cmd)})
    msg += u' containing "{0}"'.format(' '.join(rav_cmd))

    rav_result = ravelry_api('/yarns/search.json', parms)
    
    return (rav_result, msg, parms)


def ravelry_yarn(rav_cmd):

    (rav_result, msg, parms) = ravelry_api_yarn(rav_cmd)

    if rav_result['paginator']['results'] == 0:
        return (None,None)

    attachments = []
    for info in rav_result['yarns']:
        
        mach_wash = info['machine_washable'] if 'machine_washable' in info else None
        if mach_wash == None or not mach_wash:
            mach_wash = 'No'
        else:
            mach_wash = 'Yes'

        organic = info['organic'] if 'organic' in info else None
        if organic == None or not organic:
            organic = 'No'
        else:
            organic = 'Yes'

        if 'yarn_weight' in info:
            description = info['yarn_weight']['name']
        else:
            description = u'roving?'

        if info['gauge_divisor'] != None:
            gauge_range = []
            if info['min_gauge'] != None:
                gauge_range.append(str(info['min_gauge']))
            if info['max_gauge'] != None:
                gauge_range.append(str(info['max_gauge']))

            description += u', {0} sts = {1} in'.format(' to '.join(gauge_range), info['gauge_divisor'])

        description += u', {0} g, {1} yds'.format(info['grams'],info['yardage'])

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

    parms = {'photo':'yes', 'page_size':'5', 'sort':'best'}
    msg = u'Pattern search results for:'
    
    filter_free = 'free' in rav_cmd
    if filter_free:
        rav_cmd.remove('free')
        msg += u' free'

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
        msg += u' {0}'.format( ' or '.join(filter_craft) )

    if len(filter_weight) > 0:
        parms.update({'weight': '|'.join(filter_weight)})
        msg += u' with {0} yarn'.format( ' or '.join(filter_weight) )

    parms.update({'query':' '.join(rav_cmd)})
    msg += u' containing "{0}"'.format(' '.join(rav_cmd))

    search_query = '&'.join([ k + '=' + requests.utils.quote(v) for (k,v) in parms.items() if k != 'page_size'])
    search_url = 'http://www.ravelry.com/patterns/search#' + search_query

    msg += u'\n(<{0}|search on ravelry>)'.format(search_url)


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


