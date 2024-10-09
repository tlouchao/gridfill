import maya.cmds as cmds
import re

def gridfill():

    errStr = "Please select an edge loop"

    sl = cmds.ls(selection=True)
    
    # check if mesh is selected
    if not sl:
        cmds.error("Nothing selected. " + errStr)

    if not cmds.objectType(sl, isType="mesh"):
        cmds.error(f"Type \"{cmds.objectType(sl)}\" selected. " + errStr)

    # check if edge loop is selected
    sl = sl[0]
    matches = re.search('([0-9]+):([0-9]+)', sl)
    if not matches or len(matches.groups()) != 2:
        cmds.error(errStr)

    # inclusive range (includes beginIdx)
    beginIdx = int(matches.group(1))
    endIdx = int(matches.group(2))

    num_sledge = (endIdx - beginIdx) + 1
    half_sledge = num_sledge // 2
    midIdx = beginIdx + half_sledge

    if (num_sledge % 2 == 1):
        cmds.warning("Please select an even number of edges")

    shapeNode = cmds.listRelatives(sl, parent=True)[0]
    objNode = cmds.listRelatives(shapeNode, parent=True)[0]

    # ----------------- GRID FILL ----------------- #

    totalEdges = cmds.polyEvaluate(sl, edge=True)

    cmds.polyCloseBorder()
    cmds.select(f'{objNode}.vtx[{beginIdx}]')
    cmds.select(f'{objNode}.vtx[{midIdx}]', add=True)
    cmds.polySplit(insertpoint=[(beginIdx, 0), (midIdx, 0)])

    # select the new edge
    cmds.select(f'{objNode}.e[{totalEdges}]')
    
    offset = 2
    divisions = half_sledge - offset - 1

    # subdivide edge
    cmds.polySubdivideEdge(divisions=divisions)

    # edges adjacent to new edge
    i = beginIdx + 2; j = endIdx - 1; k = totalEdges + 1
    for d in range(0, divisions):
        cmds.polySplit(insertpoint=[(i, 0), (k, 0), (j, 0)])
        i += 1; j -= 1; k += 1

gridfill()