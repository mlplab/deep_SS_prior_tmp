#!/usr/bin/zsh


CMDNAME=`basename $0`


# batch_size=64
# epoch=150
dataset="Harvard"
concat = "False"
model_name=("HSCNN HSI_Network Attention_HSI_None Attention_HSI_GAP Attention_HSI_GVP")


while getopts d:c:m: OPT
do
    echo "$OPTARG"
    case $OPT in
        d) dataset=$OPTARG ;;
        c) concat=$OPTARG
        m) model_name=$OPTARG ;;
        *) echo "Usage: $CMDNAME [-b batch size] [-e epoch]" 1>&2
            exit 1;;
    esac
done


echo $dataset


model_name=( `echo $model_name | tr ' ' ' '` )
for name in $model_name[@]; do
    echo $name
done
for name in $model_name[@]; do
    python evaluate_reconst_sh.py -d $dataset -c $concat -m $name
done