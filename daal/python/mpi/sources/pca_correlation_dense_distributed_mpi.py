# file: pca_correlation_dense_distributed_mpi.py
# ==============================================================
#
# SAMPLE SOURCE CODE - SUBJECT TO THE TERMS OF SAMPLE CODE LICENSE AGREEMENT,
# http://software.intel.com/en-us/articles/intel-sample-source-code-license-agreement/
#
# Copyright (C) Intel Corporation
#
# THIS FILE IS PROVIDED "AS IS" WITH NO WARRANTIES, EXPRESS OR IMPLIED, INCLUDING BUT
# NOT LIMITED TO ANY IMPLIED WARRANTY OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE, NON-INFRINGEMENT OF INTELLECTUAL PROPERTY RIGHTS.
#
# =============================================================

#
# !  Content:
# !    Python sample of principal component analysis (PCA) using the correlation
# !    method in the distributed processing mode
# !
# !*****************************************************************************

#
## <a name="DAAL-SAMPLE-PY-PCA_CORRELATION_DENSE_DISTRIBUTED"></a>
## \example pca_correlation_dense_distributed_mpi.py
#

import os
import sys
from os.path import join as jp

from mpi4py import MPI

from daal import step1Local, step2Master
from daal.algorithms import pca
from daal.data_management import OutputDataArchive, InputDataArchive, FileDataSource, DataSourceIface

utils_folder = os.path.realpath(os.path.abspath(jp(os.environ['DAALROOT'], 'examples', 'python', 'source')))
if utils_folder not in sys.path:
    sys.path.insert(0, utils_folder)
from utils import printNumericTable

DATA_PREFIX = jp('data', 'distributed')

# Input data set parameters
nBlocks = 4
MPI_ROOT = 0

datasetFileNames = [
    jp(DATA_PREFIX, 'pca_normalized_1.csv'),
    jp(DATA_PREFIX, 'pca_normalized_2.csv'),
    jp(DATA_PREFIX, 'pca_normalized_3.csv'),
    jp(DATA_PREFIX, 'pca_normalized_4.csv')
]

if __name__ == "__main__":

    comm = MPI.COMM_WORLD
    rankId = comm.Get_rank()

    # Initialize FileDataSource to retrieve the input data from a .csv file
    dataSource = FileDataSource(datasetFileNames[rankId],
                                DataSourceIface.doAllocateNumericTable,
                                DataSourceIface.doDictionaryFromContext)

    # Retrieve the input data
    dataSource.loadDataBlock()

    # Create an algorithm for principal component analysis using the correlation method on local nodes
    localAlgorithm = pca.Distributed(step1Local)

    # Set the input data set to the algorithm
    localAlgorithm.input.setDataset(pca.data, dataSource.getNumericTable())

    # Compute PCA decomposition
    pres = localAlgorithm.compute()

    # Serialize partial results required by step 2
    dataArch = InputDataArchive()
    pres.serialize(dataArch)

    nodeResults = dataArch.getArchiveAsArray()

    # Transfer partial results to step 2 on the root node
    serializedData = comm.gather(nodeResults)

    if rankId == MPI_ROOT:
        # Create an algorithm for principal component analysis using the correlation method on the master node
        masterAlgorithm = pca.Distributed(step2Master)

        for i in range(nBlocks):
            # Deserialize partial results from step 1
            dataArch = OutputDataArchive(serializedData[i])

            dataForStep2FromStep1 = pca.PartialResult(pca.correlationDense)
            dataForStep2FromStep1.deserialize(dataArch)

            # Set local partial results as input for the master-node algorithm
            masterAlgorithm.input.add(pca.partialResults, dataForStep2FromStep1)

        # Merge and finalizeCompute PCA decomposition on the master node
        masterAlgorithm.compute()
        res = masterAlgorithm.finalizeCompute()

        # Print the results
        printNumericTable(res.get(pca.eigenvalues), "Eigenvalues:")
        printNumericTable(res.get(pca.eigenvectors), "Eigenvectors:")
