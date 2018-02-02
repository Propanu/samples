#!/bin/bash
#==============================================================
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

##  Content:
##     Intel(R) Data Analytics Acceleration Library samples
##******************************************************************************
# Don't forget to set the env below
# linux:
#  export JAVA_HOME=/usr/intel/pkgs/java/1.7.0.45-64/jre/
#  export PATH=/usr/local/hadoop/bin:/usr/local/spark/bin:/usr/intel/pkgs/java/1.7.0.45-64/bin:$PATH
#  export HADOOP_CONF_DIR=/usr/local/hadoop/etc/hadoop/
#  export DAALROOT=${PWD}/../../../daal
#  export CLASSPATH=/usr/local/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-client-common-2.5.1.jar:/usr/local/hadoop/share/hadoop/common/hadoop-common-2.5.1.jar:/usr/local/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-client-core-2.5.1.jar:/usr/local/spark/core/target/spark-core_2.10-1.1.0.jar:/usr/local/spark/mllib/target/spark-mllib_2.10-1.1.0.jar:${DAALROOT}/lib/daal.jar
#  export SCALA_JARS=/tmp/scala-library-2.10.4.jar

help_message() {
    echo "Usage: launcher.sh {arch|help}"
    echo "arch          - can be ia32 or intel64, optional for building examples."
    echo "help          - print this message"
    echo "Example: launcher.sh ia32 or launcher.sh intel64"
}

daal_ia=
first_arg=$1

while [ "$1" != "" ]; do
    case $1 in
        ia32|intel64)          daal_ia=$1
                               ;;
        help)                  help_message
                               exit 0
                               ;;
        *)                     break
                               ;;
    esac
    shift
done

if [ "${daal_ia}" != "ia32" -a "${daal_ia}" != "intel64" ]; then
    echo Bad argument arch = ${first_arg} , must be ia32 or intel64
    help_message
    exit 1
fi

# Setting CLASSPATH to build jar
export CLASSPATH=${SPARK_HOME}/jars/spark-core_2.11-2.0.0.jar:${SPARK_HOME}/jars/spark-sql_2.11-2.0.0.jar:${SPARK_HOME}/jars/spark-catalyst_2.11-2.0.0.jar:${DAALROOT}/lib/daal.jar:$CLASSPATH
export CLASSPATH=${SCALA_JARS}:$CLASSPATH

# Setting paths by OS
os_name=`uname -s`
if [ "${os_name}" == "Darwin" ]; then
    export DYLD_LIBRARY_PATH=${DAALROOT}/lib/:${DAALROOT}/../tbb/lib/:$DYLD_LIBRARY_PATH
    #Comma-separated list of shared libs
    export SHAREDLIBS=${DAALROOT}/lib/libJavaAPI.dylib,${DAALROOT}/../tbb/lib/libtbb.dylib
else
    #Comma-separated list of shared libs
    export SHAREDLIBS=${DAALROOT}/lib/${daal_ia}_lin/libJavaAPI.so,${DAALROOT}/../tbb/lib/${daal_ia}_lin/gcc4.4/libtbb.so.2
fi

# Setting list of Spark samples to process
if [ -z ${Spark_samples_list} ]; then
    source ./daal.lst
fi

for sample in ${Spark_samples_list[@]}; do

    # Creating _results folder
    mkdir -p ./_results/${sample}

    # Creating new folders on HDFS
    hadoop fs -mkdir -p /Spark/${sample}/data > _results/${sample}/${sample}.log 2>&1

    # Putting input data on HDFS
    hadoop fs -rm /Spark/${sample}/data/* >> _results/${sample}/${sample}.log 2>&1
    hadoop fs -put data/${sample}*.csv /Spark/${sample}/data/ >> _results/${sample}/${sample}.log 2>&1

    cd _results/${sample}

    cmd="spark-submit --py-files ../../sources/distributed_hdfs_dataset.py ../../sources/spark_${sample}.py"
    echo $cmd > ${sample}.res
    `${cmd} >> ${sample}.res 2>&1`

    # Checking status
    if [ -e "${sample}.out" ]; then
        echo -e "`date +'%H:%M:%S'` PASSED\t\tpyspark ${sample}"
    else
        echo -e "`date +'%H:%M:%S'` FAILED\t\tpyspark ${sample}"
    fi
    cd ../..

done
