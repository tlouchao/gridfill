import maya.cmds as cmds
import re

def gridfill():
   
    num_sledge = 0; half_sledge = 0
    beginIdx = 0; endIdx = 0; midIdx = 0
    errStr = "Please select an edge loop."

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

    if (num_sledge % 2 == 1):
        cmds.warning("Please select an even number of edges.")

    # rest of setup
    shapeNode = cmds.listRelatives(sl, parent=True)[0]
    objNode = cmds.listRelatives(shapeNode, parent=True)[0]
    
    half_sledge = num_sledge // 2
    midIdx = beginIdx + half_sledge
    
    span = num_sledge // 4
    rows = span if span % 2 == 1 else span - 1
    cols = half_sledge - rows - 2

    # ----------------- GRID FILL ----------------- #

    totalEdges = cmds.polyEvaluate(sl, edge=True)
    cmds.polyCloseBorder()

    i = ((beginIdx - ((span - 1) // 2)) % beginIdx) + beginIdx
    j = ((midIdx + ((span - 1) // 2)) % beginIdx) + beginIdx
    k = totalEdges
    ii = i # save begin index

    p = 0
    while p < rows:
        # create edge
        cmds.select(f'{objNode}.vtx[{i}]')
        cmds.select(f'{objNode}.vtx[{j}]', add=True)
        cmds.polySplit(insertpoint=[(i, 0), (j, 0)])
        # subdivide edge
        cmds.select(f'{objNode}.e[{k}]')
        cmds.polySubdivideEdge(divisions=cols)
        # increment
        p += 1
        if p == rows:
            break
        else:
            i = ((i + 1) % beginIdx) + beginIdx
            j = ((j - 1) % beginIdx) + beginIdx
            k += cols + 1

    i = ((i + 2) % beginIdx) + beginIdx 
    j = ((ii - 2) % beginIdx) + beginIdx
    k = totalEdges + 1

    q = 0
    while q < cols:
        # create edge
        cmds.select(f'{objNode}.vtx[{i}]')
        cmds.select(f'{objNode}.vtx[{j}]', add=True)
        # create intermediate points
        kcol = k
        orig = (j, 0); dest = (kcol, 0)
        for _ in range(0, rows):
            cmds.polySplit(insertpoint=[orig, dest])
            kcol += cols + 1
            orig = dest; dest = (kcol, 0)
        cmds.polySplit(insertpoint=[orig, (i, 0)])
        # increment
        q += 1
        if q == span - 1:
            break
        else:
            i = ((i + 1) % beginIdx) + beginIdx
            j = ((j - 1) % beginIdx) + beginIdx
            k += 1

gridfill()