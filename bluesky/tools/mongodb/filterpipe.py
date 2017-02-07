"""
    Filterpipe to pull required data from mongodb database

"""

from time import time

def getfilter(filtertype, mintime, maxtime, supermdb):
    """ Returns filter """
    if filtertype == 'replay' or filtertype == 'live':
        if supermdb and filtertype == 'replay':
            filterpipe = [{'$match' : { \
                            'ts' : {'$gte' : mintime, '$lt' : maxtime}\
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

        if filtertype == 'live':
            mintime = time() - 300
            maxtime = time()

            filterpipe = [{'$match' : { \
                            'icao' : {'$ne' : ''}, \
                            'mdl' : {'$ne' : ''}, \
                            'ts' : {'$gte' : mintime, '$lt' : maxtime},\
                            'loc.lat' : {'$gte' : 50.5, '$lt': 54}, \
                            'loc.lng' : {'$gte' : 2.5, '$lt' : 7.5} \
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

    elif filtertype == 'createsuperset':
        filterpipe = [{'$match' : { \
                            'icao' : {'$ne' : ''}, \
                            'mdl' : {'$ne' : ''}, \
                            'ts' : {'$gte' : mintime, '$lt' : maxtime}, \
                            'loc.lat' : {'$gte' : 50.5, '$lt': 54}, \
                            'loc.lng' : {'$gte' : 2.5, '$lt' : 7.5} \
                            } \
                        }, \
                        {'$out' : 'tempsuperset'} \
                ]
        return filterpipe

    else:
        print "ERROR: Wrong filter pipe type"
