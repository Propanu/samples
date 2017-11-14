# file: linear_regression_qr_distributed_mpi.py
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
# !    Python sample of multiple linear regression in the distributed processing
# !    mode.
# !
# !    The program trains the multiple linear regression model on a training
# !    data set with a QR decomposition-based method and computes regression
# !    for the test data.
# !*****************************************************************************

#
## <a name="DAAL-SAMPLE-PY-LINEAR_REGRESSION_QR_DISTRIBUTED"></a>
## \example linear_regression_qr_distributed_mpi.py
#

import os
import sys
from os.path import join as jp

from mpi4py import MPI

from daal import step1Local, step2Master
from daal.algorithms.linear_regression import training, prediction
from daal.data_management import (
    DataSourceIface, FileDataSource, OutputDataArchive, InputDataArchive,
    HomogenNumericTable, MergedNumericTable, NumericTableIface
)

utils_folder = os.path.realpath(os.path.abspath(jp(os.environ['DAALROOT'], 'examples', 'python', 'source')))
if utils_folder not in sys.path:
    sys.path.insert(0, utils_folder)
from utils import printNumericTable

DATA_PREFIX = jp('data', 'distributed')
trainDatasetFileNames = [
    jp(DATA_PREFIX, 'linear_regression_train_1.csv'),
    jp(DATA_PREFIX, 'linear_regression_train_2.csv'),
    jp(DATA_PREFIX, 'linear_regression_train_3.csv'),
    jp(DATA_PREFIX, 'linear_regression_train_4.csv')
]
testDatasetFileName = jp(DATA_PREFIX, 'linear_regression_test.csv')

nBlocks = 4
nFeatures = 10           # Number of features in training and testing data sets
nDependentVariables = 2  # Number of dependent variables that correspond to each observation

MPI_ROOT = 0

trainingResult = None
predictionResult = None


def trainModel():
    global trainingResult

    # Initialize FileDataSource to retrieve the input data from a .csv file
    trainDataSource = FileDataSource(trainDatasetFileNames[rankId],
                                     DataSourceIface.notAllocateNumericTable,
                                     DataSourceIface.doDictionaryFromContext)

    # Create Numeric Tables for training data and labels
    trainData = HomogenNumericTable(nFeatures, 0, NumericTableIface.doNotAllocate)
    trainDependentVariables = HomogenNumericTable(nDependentVariables, 0, NumericTableIface.doNotAllocate)
    mergedData = MergedNumericTable(trainData, trainDependentVariables)

    # Retrieve the data from the input file
    trainDataSource.loadDataBlock(mergedData)

    # Create an algorithm object to train the multiple linear regression model based on the local-node data
    localAlgorithm = training.Distributed(step1Local, method=training.qrDense)

    # Pass a training data set and dependent values to the algorithm
    localAlgorithm.input.set(training.data, trainData)
    localAlgorithm.input.set(training.dependentVariables, trainDependentVariables)

    # Train the multiple linear regression model on local nodes
    pres = localAlgorithm.compute()

    # Serialize partial results required by step 2
    dataArch = InputDataArchive()
    pres.serialize(dataArch)

    nodeResults = dataArch.getArchiveAsArray()

    # Transfer partial results to step 2 on the root node
    serializedData = comm.gather(nodeResults)

    if rankId == MPI_ROOT:
        # Create an algorithm object to build the final multiple linear regression model on the master node
        masterAlgorithm = training.Distributed(step2Master, method=training.qrDense)

        for i in range(nBlocks):
            # Deserialize partial results from step 1
            dataArch = OutputDataArchive(serializedData[i])

            dataForStep2FromStep1 = training.PartialResult()
            dataForStep2FromStep1.deserialize(dataArch)

            # Set the local multiple linear regression model as input for the master-node algorithm
            masterAlgorithm.input.add(training.partialModels, dataForStep2FromStep1)

        # Merge and finalizeCompute the multiple linear regression model on the master node
        masterAlgorithm.compute()
        # Retrieve the algorithm results
        trainingResult = masterAlgorithm.finalizeCompute()

        printNumericTable(trainingResult.get(training.model).getBeta(), "Linear Regression coefficients:")


def testModel():

    # Initialize FileDataSource to retrieve the input data from a .csv file
    testDataSource = FileDataSource(testDatasetFileName,
                                    DataSourceIface.doAllocateNumericTable,
                                    DataSourceIface.doDictionaryFromContext)

    # Create Numeric Tables for testing data and ground truth values
    testData = HomogenNumericTable(nFeatures, 0, NumericTableIface.doNotAllocate)
    testGroundTruth = HomogenNumericTable(nDependentVariables, 0, NumericTableIface.doNotAllocate)
    mergedData = MergedNumericTable(testData, testGroundTruth)

    # Retrieve the data from an input file
    testDataSource.loadDataBlock(mergedData)

    # Create an algorithm object to predict values of multiple linear regression
    algorithm = prediction.Batch()

    # Pass a testing data set and the trained model to the algorithm
    algorithm.input.setTable(prediction.data, testData)
    algorithm.input.setModel(prediction.model, trainingResult.get(training.model))

    # Predict values of multiple linear regression
    predictionResult = algorithm.compute()

    printNumericTable(predictionResult.get(prediction.prediction),
                      "Linear Regression prediction results: (first 10 rows):",
                      10)
    printNumericTable(testGroundTruth, "Ground truth (first 10 rows):", 10)

if __name__ == "__main__":

    comm = MPI.COMM_WORLD
    comm_size = comm.Get_size()
    rankId = comm.Get_rank()

    trainModel()

    if rankId == MPI_ROOT:
        testModel()
