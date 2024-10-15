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
from enum import Enum

mayaMainWindowPtr = MQtUtil.mainWindow() 
mayaMainWindow = wrapInstance(int(mayaMainWindowPtr), QWidget)


class Face(Enum):

    """Enumeration class to store grid fill settings"""

    GRID=0
    NGON=1
    NONE=2


class GridFillUI(QWidget):

    """ 
    Add functionality to the UI from QT Designer
    On confirmation, apply grid fill to the center face
    """
    
    def __init__(self):
        super().__init__()

        title = "Grid Fill Tool"
        self.setParent(mayaMainWindow)
        self.setWindowFlags(Qt.Window)
        self.setFixedSize(360, 300)
        self.setWindowTitle(title)
        self.setLogger(title)
        self.initUI()
        self.connectUI()


    def setLogger(self, title):

        """Initialize the logger"""

        fmt = logging.Formatter("%(name)s %(levelname)-8s: %(message)s")
        handler = logging.StreamHandler()
        handler.setFormatter(fmt)      
        self.logger = logging.getLogger(title)

        [self.logger.removeHandler(h) for h in self.logger.handlers]
        self.logger.addHandler(handler)
        self.logger.propagate = False

        self.logger.setLevel(logging.INFO)


    def initUI(self):

        """Initialize the UI"""

        # load the QT Designer File
        loader = QUiLoader()
        ws = cmds.workspace(q=True, rd=True)
        file = QFile(ws + "/scripts/gridfill.ui")
        file.open(QFile.ReadOnly)

        self.ui = loader.load(file, parentWidget=self)
        file.close()

        # additional setup for radio buttons
        self.ui.faceButtonGroup.setId(self.ui.faceTypeDefault, Face.GRID.value)
        self.ui.faceButtonGroup.setId(self.ui.faceTypeNgon, Face.NGON.value)
        self.ui.faceButtonGroup.setId(self.ui.faceTypeNone, Face.NONE.value)


    def connectUI(self):

        """Connect signals and slots"""

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
        self.ui.spinBoxOffset.editingFinished.connect(spinBoxMapper.map)
        self.ui.spinBoxInset.editingFinished.connect(spinBoxMapper.map)
        self.ui.spinBoxLoops.editingFinished.connect(spinBoxMapper.map)

        # sliders
        self.ui.sliderOffset.valueChanged.connect(sliderMapper.map)
        self.ui.sliderInset.valueChanged.connect(sliderMapper.map)
        self.ui.sliderLoops.valueChanged.connect(sliderMapper.map)

        # buttons
        self.ui.btnApplyAndClose.clicked.connect(self.handleBtnApplyAndClose)
        self.ui.btnApply.clicked.connect(self.handleBtnApply)
        self.ui.btnClose.clicked.connect(self.handleBtnClose)


    def handleToggle(self, id):

        """Handle checkbox toggle"""

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

        """Handle spinbox edits"""

        def setMinMax(value, sig, suffix, slider):

            """Helper function to set slider minimum / maximum range"""

            m = 1000 if suffix == "Inset" else 10
            div = m * sig
            rem = value % div
            quot = (value - rem) / div
            if (quot != 0):
                if (sig >= 0):
                    slider.setMaximum((quot + 1) * div)
                    if suffix != "Loops":
                        slider.setMinimum((quot + 1) * -div)
                else:
                    slider.setMaximum((quot + 1) * -div)
                    if suffix != "Loops":
                        slider.setMinimum((quot + 1) * div)

        # get spinbox value
        suffix = id.replace("spinBox", "")
        value = getattr(self.ui, id).value()
        value = value * 100 if suffix == "Inset" else value
        # set slider value
        slider = getattr(self.ui, "slider" + suffix)
        setMinMax(value, 1 if value > 0 else -1, suffix, slider)
        self.logger.debug(f"Slider value: {value}")
        slider.setValue(value)


    def handleSliderChange(self, id):

        """Handle slider changes"""

        # get slider value
        suffix = id.replace("slider", "")
        value = getattr(self.ui, id).value()
        value = value / 100 if suffix == "Inset" else value
        self.logger.debug(f"Spin value: {value}")
        # set spinbox value
        getattr(self.ui, "spinBox" + suffix).setValue(value)


    def handleBtnClose(self):

        """On button click, close the window"""

        self.close()


    def handleBtnApplyAndClose(self):

        """On button click, apply grid fill and close the window"""

        self.handleBtnApply()
        self.handleBtnClose()


    def handleBtnApply(self):

        """On button click, apply grid fill"""

        bOffset = self.ui.checkBoxOffset.isChecked()
        nOffset = self.ui.spinBoxOffset.value()

        bInset = self.ui.checkBoxInset.isChecked()
        nInset = self.ui.spinBoxInset.value()
        nLoops = self.ui.spinBoxLoops.value()
        dirY = self.ui.directionY.isChecked()
        dirZ = self.ui.directionZ.isChecked()

        face = self.ui.faceButtonGroup.checkedId()
        if (face == Face.GRID.value):
            self.logger.info("Mode: DEFAULT")
        else:
            self.logger.info("Mode: " + Face(face).name)

        self.gridfill(bOffset=bOffset, nOffset=nOffset, 
                      bInset=bInset, nInset=nInset, nLoops=nLoops, 
                      dirY=dirY, dirZ=dirZ, face=face)


    def gridfill(self, bOffset=False, nOffset=0, 
                 bInset=False, nInset=0, nLoops=0, 
                 dirY=False, dirZ=True, face=Face.GRID.value):
    
        """Grid Fill Setup and Inset

        Args:
            bOffset (bool): Enable offset. Defaults to False.
            nOffset (int): Number to offset. Defaults to 0.
            bInset (bool): Enable inset. Defaults to False.
            nInset (int): Inset width. Defaults to 0.
            nLoops (int): Number of inset edge loops. Defaults to 0.
            dirY (bool): Extend inset along Y-axis. Defaults to False.
            dirZ (bool): Extend inset along Z-axis. Defaults to True.
            face (int): Grid fill behavior. Defaults to 0. Can be 0, 1, or 2.
        """        
    
        try:
            # start transaction
            cmds.undoInfo(openChunk=True, infinity=True, chunkName='GridFill')

            # validation
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

                sl = cmds.ls(selection=True) # reselect edge
            
            # handle grid fill behavior
            match face:

                 # do nothing
                case Face.NONE.value:
                    pass
                 # fill hole
                case Face.NGON.value:
                    cmds.polyCloseBorder()               
                # grid fill
                case Face.GRID.value | _:
                    self.gridfillImpl(sl, bOffset=bOffset, nOffset=nOffset)

            self.logger.info("Completed Grid Fill")

        except Exception as e:
            self.logger.exception(e)
        finally:
            # end transaction
            cmds.undoInfo(closeChunk=True)


    def gridfillImpl(self, sl, bOffset=False, nOffset=0):
    
        """Grid Fill Implementation

        Args:
            sl (string array): selected edge loop as a list of strings.
            bOffset (bool): Enable offset. Defaults to False.
            nOffset (int): Number to offset. Defaults to 0.
        """

        def selectIdx(idx, n):

            """Helper function to select edge loop index"""

            ret = idx
            if idx < 0:
                ret = (n + idx) % n
            elif idx >= n:
                ret = idx % n
            return ret

        cmds.polyCloseBorder()

        mapEdge = dict()
        rowBeginEdge = cmds.polyEvaluate(sl[0], edge=True)
        sledge = cmds.polyEvaluate(sl[0], edgeComponent=True)

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
            k = 0; i = k
            while k < sledge:
                matches = re.search(pat1, sl[i])
                if (matches):
                    v = int(matches.group(1))
                    mapEdge[k] = v
                    k += 1
                else:
                    matches = re.search(pat2, sl[i])
                    beginIdx = int(matches.group(1))
                    endIdx = int(matches.group(2))
                    for v in range(beginIdx, endIdx + 1):
                        mapEdge[k] = v
                        k += 1
                i += 1

        # rest of setup         
        span = sledge // 4
        rows = span if span % 2 == 1 else span - 1
        cols = sledge // 2 - rows - 2

        shapeNode = cmds.listRelatives(sl[0], parent=True)[0]
        objNode = cmds.listRelatives(shapeNode, parent=True)[0]

        # ------- create edges parallel to edge from start vertex -------- #

        # handle offset
        offset = nOffset if bOffset else 0
        i = selectIdx(0 + offset, sledge)
        j = selectIdx((sledge // 2) + offset, sledge)
        self.logger.debug(f"Begin i: {i}, Begin j: {j}")

        i = selectIdx(i - ((span - 1) // 2), sledge)
        j = selectIdx(j + ((span - 1) // 2), sledge)
        self.logger.debug(f"Span i: {i}, Span j: {j}")
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
                i = selectIdx(i + 1, sledge)
                j = selectIdx(j - 1, sledge)
                k += cols + 1
        
        # ----- create edges perpendicular to edge from start vertex ----- #

        colBeginEdge = cmds.polyEvaluate(sl[0], edge=True)
        i = selectIdx(i + 2, sledge)
        j = selectIdx(ii - 2, sledge)
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
                i = selectIdx(i + 1, sledge)
                j = selectIdx(j - 1, sledge)
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

    
def main():
    gui = GridFillUI()
    gui.show()
    return gui


if __name__ == '__main__':
    main()
