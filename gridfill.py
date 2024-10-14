from maya import cmds
from maya import mel
from maya.OpenMayaUI import MQtUtil 

# Import Qt
from PySide6.QtCore import Qt, QFile, QSize, QSignalMapper
from PySide6.QtWidgets import QWidget
from PySide6.QtUiTools import QUiLoader
from shiboken6 import wrapInstance

import re
import logging

mayaMainWindowPtr = MQtUtil.mainWindow() 
mayaMainWindow = wrapInstance(int(mayaMainWindowPtr), QWidget) 

class GridFillUI(QWidget):
    def __init__(self):
        super().__init__()

        title = "Grid Fill Tool"
        self.setParent(mayaMainWindow)
        self.setWindowFlags(Qt.Window)
        self.setFixedSize(360, 270)
        self.setWindowTitle(title)
        self.setLogger(title)
        self.initUI()
        self.connectUI()


    def setLogger(self, title):
        fmt = logging.Formatter("%(name)s %(levelname)-8s: %(message)s")
        handler = logging.StreamHandler()
        handler.setFormatter(fmt)      
        self.logger = logging.getLogger(title)

        [self.logger.removeHandler(h) for h in self.logger.handlers]
        self.logger.addHandler(handler)
        self.logger.propagate = False

        self.logger.setLevel(logging.INFO)


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
            self.ui.directionY.setEnabled(checked)
            self.ui.directionZ.setEnabled(checked)
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
        dirY = self.ui.directionY.isChecked()
        dirZ = self.ui.directionZ.isChecked()

        self.apply(bOffset=bOffset, nOffset=nOffset, 
                   bInset=bInset, nInset=nInset, 
                   nLoops=nLoops, dirY=dirY, dirZ=dirZ)


    def handleBtnClose(self):
        self.close()


    def apply(self, bOffset=False, nOffset=0, 
              bInset=False, nInset=0, 
              nLoops=0, dirY=False, dirZ=True):
    
        try:
            # start transaction
            cmds.undoInfo(openChunk=True, infinity=True, chunkName='GridFill')

            # -------------------------validation ---------------------------- #

            sledge = 0
            mapEdge = dict()
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

            # check if even number of selected edges
            sledge = cmds.polyEvaluate(sl[0], edgeComponent=True)
            if (sledge % 2 == 1):
                self.logger.warning("Please select an even number of edges.")

            # handle inset and reselect edge
            if (bInset):
                if (dirY):
                    cmds.polyExtrudeEdge(*sl, off=nInset, divisions=nLoops + 1)
                if (dirZ):
                    nInset = -nInset
                    cmds.polyExtrudeEdge(*sl, ltz=nInset, divisions=nLoops + 1)
                sl = cmds.ls(selection=True)
            
            rowBeginEdge = cmds.polyEvaluate(sl[0], edge=True)

            # map consecutive edges 
            if (len(sl) == 1):
                pat = re.compile(r'\[([0-9]+):([0-9]+)\]')
                matches = re.search(pat, sl[0])
                v = int(matches.group(1))
                for k in range(sledge):
                    mapEdge[k] = v + k
                    k += 1

            # map non-consecutive edges     
            else:
                pat1 = re.compile(r'\[([0-9]+)\]')
                pat2 = re.compile(r'\[([0-9]+):([0-9]+)\]')
                k = 0; sk = k
                while k < sledge:
                    matches = re.search(pat1, sl[sk])
                    if (matches):
                        v = int(matches.group(1))
                        mapEdge[k] = v
                        k += 1
                    else:
                        matches = re.search(pat2, sl[sk])
                        beginIdx = int(matches.group(1))
                        endIdx = int(matches.group(2))
                        for v in range(beginIdx, endIdx + 1):
                            mapEdge[k] = v
                            k += 1
                    sk += 1

            # rest of setup         
            span = sledge // 4
            rows = span if span % 2 == 1 else span - 1
            cols = sledge // 2 - rows - 2

            shapeNode = cmds.listRelatives(sl[0], parent=True)[0]
            objNode = cmds.listRelatives(shapeNode, parent=True)[0]

            # ------- create edges parallel to edge from start vertex -------- #

            cmds.polyCloseBorder()

            # handle offset
            offset = nOffset if bOffset else 0
            i = 0 + offset; j = (sledge // 2) + offset

            i = self.selectIdx(i - ((span - 1) // 2), sledge)
            j = self.selectIdx(j + ((span - 1) // 2), sledge)
            k = rowBeginEdge
            ii = i # save begin index

            p = 0
            while p < rows:
                # create edge
                cmds.polySplit(insertpoint=[(mapEdge[i], 0), (mapEdge[j], 0)])
                # subdivide edge
                cmds.select(f'{objNode}.e[{k}]')
                cmds.polySubdivideEdge(divisions=cols)
                # increment
                p += 1
                if p == rows:
                    break
                else:
                    i = self.selectIdx(i + 1, sledge)
                    j = self.selectIdx(j - 1, sledge)
                    k += cols + 1
            
            # ----- create edges perpendicular to edge from start vertex ----- #

            colBeginEdge = cmds.polyEvaluate(sl[0], edge=True)
            i = self.selectIdx(i + 2, sledge)
            j = self.selectIdx(ii - 2, sledge)
            k = rowBeginEdge + 1

            q = 0
            while q < cols:
                # create intermediate points
                kcol = k
                orig = (mapEdge[j], 0); dest = (kcol, 0)
                for _ in range(rows):
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
            
            # ----------------------  edit edge flow ------------------------- #

            if not ((rows == 1) or (cols == 1)):
                self.logger.debug('Editing edge flow')

                s = 0
                while s < ((span - 1) // 2):

                    # select row
                    t = rowBeginEdge + 1 + (s * (cols + 1))
                    edgeSelect = f'{objNode}.e[{t}:{t + (cols - 2)}]'
                    cmds.select(edgeSelect)
                    self.logger.debug('Row : ' + edgeSelect)

                    # select opposite row
                    t = (rowBeginEdge + 1) + ((rows - 1 - s) * (cols + 1))
                    edgeSelect = f'{objNode}.e[{t}:{t + (cols - 2)}]'
                    cmds.select(edgeSelect, add=True)
                    self.logger.debug('Opposite Row : ' + edgeSelect)

                    cmds.polyEditEdgeFlow(adjustEdgeFlow=0)

                    # select column
                    t = colBeginEdge + 1 + (s * (cols + 1))
                    edgeSelect = f'{objNode}.e[{t}:{t + (rows - 2)}]'
                    cmds.select(edgeSelect)
                    self.logger.debug('Column : ' + edgeSelect)

                    # select opposite column
                    t = (colBeginEdge + 1) + ((cols - 1 - s) * (rows + 1))
                    edgeSelect = f'{objNode}.e[{t}:{t + (rows - 2)}]'
                    cmds.select(edgeSelect, add=True)
                    self.logger.debug('Opposite Column : ' + edgeSelect)

                    cmds.polyEditEdgeFlow(adjustEdgeFlow=0)
                    
                    s += 1

            # select initial edge loop
            cmds.select(sl)
            self.logger.info("Completed Grid Fill")

        except Exception as e:
            self.logger.exception(e)
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
