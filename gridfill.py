import maya.cmds as cmds
import maya.OpenMaya as OpenMaya

import re

def gridfill():

    print("Hello, world!")

    errStr = "Please select an edge loop"

    # Check if mesh is selected
    sl = cmds.ls(selection=True)[0]
    if not sl:
        cmds.error("Nothing selected." + errStr)
    elif not cmds.objectType(sl, isType="mesh"):
        cmds.error(f"Type \"{cmds.objectType(sl)}\" selected. " + errStr)

    # check if edge loop is selected
    matches = re.search('([0-9]+):([0-9]+)', sl)
    if not matches or len(matches.groups()) != 2:
        cmds.error(errstr)


    beginIdx = matches.group(1)
    endIdx = matches.group(2)

    shapeNode = cmds.listRelatives(sl, shapes=True)
    nodeType = cmds.nodeType(shapeNode)
    totalEdges = cmds.polyEvaluate(sl, edge=True)

    print(totalEdges)
    print(beginIdx)
    print(endIdx)

gridfill()