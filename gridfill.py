from maya import cmds
from maya import mel
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

        bOffset = self.ui.checkBoxOffset.isChecked()
        nOffset = self.ui.spinBoxOffset.value()

        bInset = self.ui.checkBoxInset.isChecked()
        nInset = self.ui.spinBoxInset.value()
        nLoops = self.ui.spinBoxLoops.value()

        self.apply(bOffset=bOffset, nOffset=nOffset, 
                   bInset=bInset, nInset=nInset, nLoops=nLoops)


    def handleBtnClose(self):
        self.close()


    def apply(self, bOffset=False, nOffset=0, bInset=False, nInset=0, nLoops=0):
    
        try:
            # start transaction
            cmds.undoInfo(openChunk=True, infinity=True, chunkName='GridFill')

            # validation ----------------------------------------------------- #
            sledge = 0; half_sledge = 0
            beginIdx = 0; endIdx = 0; midIdx = 0
            mapEdge = dict(); mapVtx = dict()
            errStr = "Please select an edge loop."

            # enforce edge loop selection
            mel.eval('polySelectSp -loop')
            
            # check if selected
            sl = cmds.ls(selection=True)
            if not sl:
                cmds.error("Nothing selected. " + errStr)

            if not cmds.objectType(sl[0], isType="mesh"):
                typeErrStr = f"Type \"{cmds.objectType(sl)}\" selected. "
                cmds.error(typeErrStr + errStr)

            slv = cmds.polyListComponentConversion(toVertex=True)
            shapeNode = cmds.listRelatives(sl, parent=True)[0]
            objNode = cmds.listRelatives(shapeNode, parent=True)[0]

            if (len(sl) == 1):

                sl = sl[0]
                matches = re.search('([0-9]+):([0-9]+)', sl)
                
                # inclusive range (includes end index)
                beginIdx = int(matches.group(1))
                endIdx = int(matches.group(2))
                sledge = ((endIdx + 1) - beginIdx)
                if (sledge % 2 == 1):
                    cmds.warning("Please select an even number of edges.")
                mapBeginIdx = 0; mapMidIdx = sledge // 2; mapEndIdx = sledge
                
                k = 0
                for k in range(sledge):
                    mapEdge[k] = beginIdx + k
                    mapVtx[k] = beginIdx + k
                    k += 1
                    
            else:
                print(len(sl))

            # rest of setup            
            half_sledge = sledge // 2
            midIdx = beginIdx + half_sledge

            span = sledge // 4
            rows = span if span % 2 == 1 else span - 1
            cols = half_sledge - rows - 2

            # create edges parallel to edge from start vertex ---------------- #
            cmds.select(sl)
            rowBeginEdge = cmds.polyEvaluate(sl, edge=True)
            cmds.polyCloseBorder()
            
            i = 0; j = mapMidIdx
            i = self.selectIdx(i - ((span - 1) // 2), sledge)
            j = self.selectIdx(j + ((span - 1) // 2), sledge)
            k = rowBeginEdge
            ii = i # save begin index

            p = 0
            while p < rows:
                # create edge
                cmds.select(f'{objNode}.vtx[{mapVtx[i]}]')
                cmds.select(f'{objNode}.vtx[{mapVtx[j]}]', add=True)
                cmds.polySplit(insertpoint=[(mapEdge[i], 0), (mapEdge[j], 0)])
                # subdivide edge
                cmds.select(f'{objNode}.e[{k}]')
                cmds.polySubdivideEdge(divisions=cols)
                # increment
                p += 1
                if p == rows:
                    break
                else:
                    # i = ((i + 1) % beginIdx) + beginIdx
                    # j = ((j - 1) % beginIdx) + beginIdx
                    i = self.selectIdx(i + 1, sledge)
                    j = self.selectIdx(j - 1, sledge)
                    k += cols + 1
            
            # create edges perpendicular to edge from start vertex ----------- #
            colBeginEdge = cmds.polyEvaluate(sl, edge=True)
            i = self.selectIdx(i + 2, sledge)
            j = self.selectIdx(ii - 2, sledge)
            k = rowBeginEdge + 1

            q = 0
            while q < cols:
                # create intermediate points
                kcol = k
                orig = (mapEdge[j], 0); dest = (kcol, 0)
                for _ in range(0, rows):
                    cmds.polySplit(insertpoint=[orig, dest])
                    kcol += cols + 1
                    orig = dest; dest = (kcol, 0)
                cmds.polySplit(insertpoint=[orig, (mapEdge[i], 0)])
                # increment
                q += 1 
                if q == cols:
                    break
                else:
                    i = self.selectIdx(i + 1, sledge)
                    j = self.selectIdx(j - 1, sledge)
                    k += 1
            
            # edit edge flow ------------------------------------------------- #
            s = 0
            while s < ((span - 1) // 2):

                # rows
                t = rowBeginEdge + 1 + (s * (cols + 1))
                cmds.select(f'{objNode}.e[{t}:{t + (cols - 2)}]')
                t = (rowBeginEdge + 1) + ((rows - 1 - s) * (cols + 1))
                cmds.select(f'{objNode}.e[{t}:{t + (cols - 2)}]', add=True)
                cmds.polyEditEdgeFlow(adjustEdgeFlow=0)

                # cols
                t = colBeginEdge + 1 + (s * (cols + 1))
                cmds.select(f'{objNode}.e[{t}:{t + (rows - 2)}]')
                t = (colBeginEdge + 1) + ((cols - 1 - s) * (rows + 1))
                cmds.select(f'{objNode}.e[{t}:{t + (rows - 2)}]', add=True)
                cmds.polyEditEdgeFlow(adjustEdgeFlow=0)
                
                s += 1
            
            # select initial edge loop
            cmds.select(sl)
            print("Completed Grid Fill")

        except Exception as e:
            cmds.error(e)
        finally:
            # end transaction
            cmds.undoInfo(closeChunk=True)

    '''
    Helper function to select edge loop index
    '''
    def selectIdx(self, idx, n):
        ret = idx
        if idx < 0:
            ret = n - abs(idx)
        elif idx >= n:
            ret = abs(n - idx)
        return ret

    
def main():
    gui = GridFillUI()
    gui.show()
    return gui

if __name__ == '__main__':
    main()
