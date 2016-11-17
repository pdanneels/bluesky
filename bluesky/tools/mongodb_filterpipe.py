"""
    Filterpipe to pull required data from mongodb database

"""

from time import time

def getfilter(filtertype, mintime, maxtime):
    """ Returns filter """
    if filtertype == 'live' or filtertype == 'replay':
        if filtertype == 'live':
            mintime = time() - 300
            maxtime = time()

        filterpipe = [{'$match' : { \
                        'icao' : {'$ne' : ''}, \
                        'mdl' : {'$ne' : ''}, \
                        'ts' : {'$gte' : mintime, '$lt' : maxtime} \
                        } \
            }, \
            {'$group' : {  \
                        '_id' : '$icao', \
                        'latest' : {'$max' : '$ts'}, \
                        'objid' : {'$first' : '$$CURRENT._id'}, \
                        'loc' : {'$first' : '$$CURRENT.loc'}, \
                        'from' : {'$first' : '$$CURRENT.from'}, \
                        'mdl' : {'$first' : '$$CURRENT.mdl'}, \
                        'to' : {'$first' : '$$CURRENT.to'}, \
                        'roc' : {'$first' : '$$CURRENT.roc'}, \
                        'hdg' : {'$first' : '$$CURRENT.hdg'}, \
                        'alt' : {'$first' : '$$CURRENT.alt'}, \
                        'spd' : {'$first' : '$$CURRENT.spd'} \
                        } \
            }, \
            {'$project' : {'_id' : '$objid', \
                            'loc' : 1, \
                            'from' : 1, \
                            'mdl' : 1, \
                            'to' : 1, \
                            'roc' : 1, \
                            'ts' : '$latest', \
                            'icao' : '$_id', \
                            'hdg' : 1, \
                            'alt' : 1, \
                            'spd' : 1 \
                            }
            }]
        return filterpipe

    elif filtertype == 'metropolis':
        maxtime = mintime + 20
        filterpipe = [{'$match' : { \
                        'icao' : {'$ne' : ''}, \
                        'mdl' : {'$ne' : ''}, \
                        'ts' : {'$gte' : mintime, '$lt' : maxtime} \
                        } \
            }, \
            {'$group' : {  \
                        '_id' : '$icao', \
                        'latest' : {'$max' : '$ts'}, \
                        'objid' : {'$first' : '$$CURRENT._id'}, \
                        'loc' : {'$first' : '$$CURRENT.loc'}, \
                        'orig' : {'$first' : '$$CURRENT.from'}, \
                        'mdl' : {'$first' : '$$CURRENT.mdl'}, \
                        'dest' : {'$first' : '$$CURRENT.to'}, \
                        'roc' : {'$first' : '$$CURRENT.roc'}, \
                        'hdg' : {'$first' : '$$CURRENT.hdg'}, \
                        'alt' : {'$first' : '$$CURRENT.alt'}, \
                        'spd' : {'$first' : '$$CURRENT.spd'} \
                        } \
            }, \
            {'$project' : {'_id' : '$objid', \
                            'loc' : 1, \
                            'orig' : 1, \
                            'mdl' : 1, \
                            'dest' : 1, \
                            'roc' : 1, \
                            'ts' : '$latest', \
                            'icao' : '$_id', \
                            'hdg' : 1, \
                            'alt' : 1, \
                            'spd' : 1 \
                            }
            }]
        return filterpipe

    else:
        print "ERROR: Wrong filter pipe type"
