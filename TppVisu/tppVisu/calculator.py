'''
Created on 02.05.2015

@author: Felk
'''
from enum import Enum

from tppVisu.move import MoveCategory
from tppVisu.tables import moveFuncs
from tppVisu.tables.typeEffs import getEff
from tppVisu.util import Eff
from copy import deepcopy


class Kind(Enum):
    normal      = 'normal'
    status      = 'status'
    ohko        = 'ohko'
    notVisuable = 'notVisuable'

class MoveResult(object):
    def __init__(self, pkmn, opp, env, accuracy, kind=Kind.normal, eff=Eff.NORMAL, damage=None):
        self.pkmn = pkmn
        self.opp = opp
        self.env = env
        self.accuracy = accuracy
        self.kind = kind
        self.eff  = eff
        self.damage = damage

def calcMove(move, pkmn, opp, env):
    
    # work on local copies!
    move = deepcopy(move)
    pkmn = deepcopy(pkmn)
    opp  = deepcopy(opp)
    env  = deepcopy(env)
    
    ovwr = moveFuncs.call(move, pkmn, opp, env)
    
    if not move.visuable:
        return MoveResult(pkmn, opp, env, move.accuracy, kind=Kind.notVisuable)
    
    # calculate final accuracy
    accu = move.accuracy * (pkmn.ACC.get() / opp.EVA.get())
    # accuracy is a fixed value for OHKO moves
    if move.isOHKOMove():
        accu = 30 + (pkmn.level - opp.level)
        if accu > 100: accu = 100
        if accu < 30: move.disable()
        
    if move.isDisabled():
        return MoveResult(pkmn, opp, env, accu, eff=Eff.NOT)
    
    ##########################################################
    
    # TODO don't calculate para-nerf here
    if pkmn.status == 'par':
        pkmn.SPE *= pkmn.parMult
        
    if move.category == MoveCategory.nonDamaging:
        # No more calculating needed
        # TODO implement damage values for special attacks as well (Future sight e.g.)
        return MoveResult(pkmn, opp, env, accu, kind=Kind.status)
    elif move.category == MoveCategory.physical:
        valueAtkDef = pkmn.ATK.get() / opp.DEF.get()
    else:
        valueAtkDef = pkmn.SPA.get() / opp.SPD.get()
        
    modifierStab = 1
    if pkmn.type1 == move.type: modifierStab *= pkmn.stab
    if pkmn.type2 == move.type: modifierStab *= pkmn.stab
    
    modifierType = getEff(move.type, opp.type1)
    if opp.type2: modifierType *= getEff(move.type, opp.type2)
    
    modifierPost = getattr(pkmn.typeMults, move.type)
    
    if modifierType == 0 or modifierPost == 0:
        eff = Eff.NOT
        modifierType = pkmn.effs.NOT
    elif modifierType < 1:
        eff = Eff.WEAK
        modifierType *= pkmn.effs.WEAK * 2 # scale default (0.5) to 1 to act as multiplier
    elif modifierType > 1:
        eff = Eff.SUPER
        modifierType *= pkmn.effs.SUPER * 0.5 # scale default (2) to 1 to act as multiplier
    else:
        eff = Eff.NORMAL
        modifierType *= pkmn.effs.NORMAL
    
    if move.isOHKOMove():
        return MoveResult(pkmn, opp, env, accu, kind=Kind.ohko, eff=eff)
    
    power = ovwr.power if ovwr.power != None else (move.power, move.power)
    
    calcSetup = lambda P: (((2 * pkmn.level + 10) / 250) * valueAtkDef * P + 2) * modifierStab * modifierType * modifierPost
    predamage = tuple(calcSetup(P) for P in power)
    
    # BRN attack nerf
    if pkmn.status == 'brn' and move.category == MoveCategory.physical:
        predamage = tuple(D * pkmn.brnMult for D in predamage)
        
    damage = ovwr.damage if ovwr.damage != None else (predamage[0] * 0.85, predamage[1])
    damage = tuple(max(0, D) for D in damage)

    return MoveResult(pkmn, opp, env, accu, eff=eff, damage=damage)
