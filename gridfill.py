from maya import cmds
from maya.OpenMayaUI import MQtUtil 

# Import Qt
from PySide6.QtCore import Qt, QFile, QSize, QSignalMapper
from PySide6.QtWidgets import QWidget
from PySide6.QtUiTools import QUiLoader
from shiboken6 import wrapInstance

import re

mayaMainWindowPtr = MQtUtil.mainWindow() 
mayaMainWindow = wrapInstance(int(mayaMainWindowPtr), QWidget) 

class GridFillUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setParent(mayaMainWindow)
        self.setWindowFlags(Qt.Window)
        self.setWindowTitle("Grid Fill Tool")
        self.setFixedSize(360, 240)
        self.initUI()
        self.connectUI()


    def initUI(self):
        loader = QUiLoader()
        ws = cmds.workspace(q=True, rd=True)
        file = QFile(ws + "/scripts/gridfill.ui")
        file.open(QFile.ReadOnly)

        self.ui = loader.load(file, parentWidget=self)
        file.close()


    def connectUI(self):

        # pass source widget id to handler
        checkBoxMapper = QSignalMapper(self)
        spinBoxMapper = QSignalMapper(self)
        sliderMapper = QSignalMapper(self)

        checkBoxMapper.setMapping(self.ui.checkBoxOffset, "checkBoxOffset")
        checkBoxMapper.setMapping(self.ui.checkBoxInset, "checkBoxInset")
        spinBoxMapper.setMapping(self.ui.spinBoxOffset, "spinBoxOffset")
        spinBoxMapper.setMapping(self.ui.spinBoxInset, "spinBoxInset")
        spinBoxMapper.setMapping(self.ui.spinBoxLoops, "spinBoxLoops")
        sliderMapper.setMapping(self.ui.sliderOffset, "sliderOffset")
        sliderMapper.setMapping(self.ui.sliderInset, "sliderInset")
        sliderMapper.setMapping(self.ui.sliderLoops, "sliderLoops")

        checkBoxMapper.mappedString.connect(self.handleToggle)
        spinBoxMapper.mappedString.connect(self.handleSpinBoxChange)
        sliderMapper.mappedString.connect(self.handleSliderChange)

        # checkboxes
        self.ui.checkBoxOffset.toggled.connect(checkBoxMapper.map)
        self.ui.checkBoxInset.toggled.connect(checkBoxMapper.map)

        # spinboxes
        self.ui.spinBoxOffset.valueChanged.connect(spinBoxMapper.map)
        self.ui.spinBoxInset.valueChanged.connect(spinBoxMapper.map)
        self.ui.spinBoxLoops.valueChanged.connect(spinBoxMapper.map)

        # sliders
        self.ui.sliderOffset.valueChanged.connect(sliderMapper.map)
        self.ui.sliderInset.valueChanged.connect(sliderMapper.map)
        self.ui.sliderLoops.valueChanged.connect(sliderMapper.map)

        # buttons
        self.ui.btnApplyAndClose.clicked.connect(self.handleBtnApplyAndClose)
        self.ui.btnApply.clicked.connect(self.handleBtnApply)
        self.ui.btnClose.clicked.connect(self.handleBtnClose)


    def handleToggle(self, id):
        suffix = id.replace("checkBox", "")
        checked = getattr(self.ui, id).isChecked()
        getattr(self.ui, "spinBox" + suffix).setEnabled(checked)
        getattr(self.ui, "slider" + suffix).setEnabled(checked)
        if (suffix == "Inset"):
            self.ui.spinBoxLoops.setEnabled(checked)
            self.ui.sliderLoops.setEnabled(checked)


    def handleSpinBoxChange(self, id):
        suffix = id.replace("spinBox", "")
        value = getattr(self.ui, id).value()
        value = value * 100 if suffix == "Inset" else value
        getattr(self.ui, "slider" + suffix).setValue(value)


    def handleSliderChange(self, id):
        suffix = id.replace("slider", "")
        value = getattr(self.ui, id).value()
        value = value / 100 if suffix == "Inset" else value
        getattr(self.ui, "spinBox" + suffix).setValue(value)


    def handleBtnApplyAndClose(self):
        self.handleBtnApply()
        self.handleBtnClose()


    def handleBtnApply(self):
        doOffset = self.ui.checkBoxOffset.isChecked()
        numOffset = self.ui.spinBoxOffset.value()
        doInset = self.ui.checkBoxInset.isChecked()
        numInset = self.ui.spinBoxInset.value()
        self.gridfill(doOffset=doOffset, numOffset=numOffset, 
                      doInset=doInset, numInset=numInset)


    def handleBtnClose(self):
        self.close()


    def gridfill(self, doOffset=False, numOffset=0, doInset=False, numInset=0):
    
        try:
            # start transaction
            cmds.undoInfo(openChunk=True, infinity=True, chunkName='Grid Fill')

            # init
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

            rowBeginEdges = cmds.polyEvaluate(sl, edge=True)
            cmds.polyCloseBorder()

            i = beginIdx; j = midIdx
            if (doOffset):
                print(numOffset)
                i += numOffset; j += numOffset

            i = ((i - ((span - 1) // 2)) % beginIdx) + beginIdx
            j = ((j + ((span - 1) // 2)) % beginIdx) + beginIdx
            k = rowBeginEdges
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

            colBeginEdges = cmds.polyEvaluate(sl, edge=True)
            i = ((i + 2) % beginIdx) + beginIdx 
            j = ((ii - 2) % beginIdx) + beginIdx
            k = rowBeginEdges + 1

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
                if q == cols:
                    break
                else:
                    i = ((i + 1) % beginIdx) + beginIdx
                    j = ((j - 1) % beginIdx) + beginIdx
                    k += 1
            
            # --------------- edit edge flow --------------- #
            
            s = 1
            while s <= ((span - 1) // 2):

                # rows
                offset = rowBeginEdges + 1 + ((s - 1) * (cols + 1))
                cmds.select(f'{objNode}.e[{offset}:{offset + (cols - 2)}]')
                offset = (rowBeginEdges + 1) + ((rows - 1 - (s - 1)) * (cols + 1))
                cmds.select(f'{objNode}.e[{offset}:{offset + (cols - 2)}]', add=True)
                cmds.polyEditEdgeFlow(adjustEdgeFlow=0)

                # cols
                offset = colBeginEdges + 1 + ((s - 1) * (cols + 1))
                cmds.select(f'{objNode}.e[{offset}:{offset + (rows - 2)}]')
                offset = (colBeginEdges + 1) + ((cols - 1 - (s - 1)) * (rows + 1))
                cmds.select(f'{objNode}.e[{offset}:{offset + (rows- 2)}]', add=True)
                cmds.polyEditEdgeFlow(adjustEdgeFlow=0)
                
                s += 1
            
            # select initial edge loop
            cmds.select(sl)
            print("Completed Grid Fill")
        except Exception as e:
            print(e)
        finally:
            # end transaction
            cmds.undoInfo(closeChunk=True)

    
def main():
    gui = GridFillUI()
    gui.show()
    return gui

if __name__ == '__main__':
    main()
