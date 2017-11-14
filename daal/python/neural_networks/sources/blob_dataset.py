# file: blob_dataset.py
# ==============================================================
#
# SAMPLE SOURCE CODE - SUBJECT TO THE TERMS OF SAMPLE CODE LICENSE AGREEMENT,
# http://software.intel.com/en-us/articles/intel-sample-source-code-license-agreement/
#
# Copyright 2017 Intel Corporation
#
# THIS FILE IS PROVIDED "AS IS" WITH NO WARRANTIES, EXPRESS OR IMPLIED, INCLUDING BUT
# NOT LIMITED TO ANY IMPLIED WARRANTY OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE, NON-INFRINGEMENT OF INTELLECTUAL PROPERTY RIGHTS.
#
# =============================================================

#
# !  Content:
# !    Auxiliary functions used in Python neural networks samples
# !*****************************************************************************

import struct
from io import open

import numpy as np

from daal.data_management import HomogenTensor, SubtensorDescriptor, writeOnly, TensorIface


class ImageBlobDatasetReader:

    def __init__(self, pathToImages, batchSize):
        self._imagesNumber = 0
        self._imagesInBatch = batchSize
        self._batchCounter = 0
        self._imageChannels = 0
        self._imageHeight = 0
        self._imageWidth = 0
        self._dataFile = None
        self._imagesPosition = None
        self._classesPosition = None
        self._open(pathToImages)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._close()

    def next(self):
        """Advances the reader to next batch"""

        if not self._dataFile:
            raise RuntimeError("Can't open dataset file")

        self._batchCounter += 1

        return self._batchCounter * self._imagesInBatch <= self._imagesNumber

    def reset(self):
        """Resests reader position to the first batch"""

        self._batchCounter = 0


    def getBatch(self):
        """Returns current batch"""

        self._checkBeforeReadBatch()
        return self._readBatchFromDataset(self._dataFile, self._batchCounter - 1)

    def getGroundTruthBatch(self):
        """Returns coresponding lables of current batch"""

        self._checkBeforeReadBatch()
        return self._readGroundTruthFromDataset(self._dataFile, self._batchCounter - 1)

    def getBatchDimensions(self):
        """Returns dimensions of one batch"""

        dims = [self._imagesInBatch, self._imageChannels, self._imageHeight, self._imageWidth]
        return dims

    def getNumberOfImages(self):
        """Returns total number of images in the blob"""

        return self._imagesNumber

    def _open(self, datasetPath):
        """Opens the file containing dataset"""

        if not datasetPath:
            raise RuntimeError("Path to dataset is empty")


        self._dataFile = open(datasetPath, 'rb')
        if not self._dataFile:
            raise RuntimeError("Can't open dataset " + datasetPath)

        self._imagesNumber = self._readDWORD(self._dataFile)
        self._imageChannels = self._readDWORD(self._dataFile)
        self._imageWidth = self._readDWORD(self._dataFile)
        self._imageHeight = self._readDWORD(self._dataFile)

        imagesDataSize = self._imagesNumber * self._imageChannels * self._imageWidth * self._imageHeight

        self._imagesPosition = self._dataFile.tell()
        self._classesPosition = self._imagesPosition + imagesDataSize

    def _close(self):
        """Closes the dataset file"""

        if self._dataFile:
            self._dataFile.close()

    def _readBatchFromDataset(self, in_file, counter):
        """Reads batch of images coresponding to the current reader position"""

        imagesBatchSize = self._imagesInBatch * self._imageChannels * self._imageWidth * self._imageHeight
        batchPosition = self._imagesPosition + imagesBatchSize * counter
        in_file.seek(batchPosition)

        dataBatch = allocateTensor(np.float32, self._imagesInBatch, self._imageChannels, self._imageHeight, self._imageWidth)
        trainTensorSize = dataBatch.getSize()

        batchBlock = SubtensorDescriptor(ntype=np.float32)
        dataBatch.getSubtensor([], 0, self._imagesInBatch, writeOnly, batchBlock)
        objectsPtr = batchBlock.getArray()

        binary_data_str = in_file.read(trainTensorSize)
        objectData = np.array(struct.unpack('B' * trainTensorSize, binary_data_str), dtype=np.float32)

        for x, i in zip(np.nditer(objectsPtr, op_flags=['readwrite']), range(len(objectData))):
            x[...] = objectData[i]

        dataBatch.releaseSubtensor(batchBlock)
        return dataBatch

    def _readGroundTruthFromDataset(self, in_file, counter):
        """Reads batch of labels coresponding to the current reader position"""

        batchLabelsSize = self._imagesInBatch * 4
        batchPosition = self._classesPosition + batchLabelsSize * counter
        in_file.seek(batchPosition)

        groundTruthBatch = allocateTensor(np.intc, self._imagesInBatch, 1)

        groundTruthBlock = SubtensorDescriptor(ntype=np.intc)
        groundTruthBatch.getSubtensor([], 0, self._imagesInBatch, writeOnly, groundTruthBlock)
        groundTruthPtr = groundTruthBlock.getArray()

        for x in np.nditer(groundTruthPtr, op_flags=['readwrite']):
            x[...] = int(self._readDWORD(in_file))

        groundTruthBatch.releaseSubtensor(groundTruthBlock)
        return groundTruthBatch

    def _checkBeforeReadBatch(self):
        if not self._dataFile:
            raise RuntimeError("Can't open dataset file")

    def _readDWORD(self, stream):
        dword = struct.unpack('I', stream.read(4))[0]
        return dword


def allocateTensor(dataType, *dims):
    return HomogenTensor(dims, TensorIface.doAllocate, ntype=dataType)
