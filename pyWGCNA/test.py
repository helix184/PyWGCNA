import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
import main as WGCNA
from scipy.cluster.hierarchy import dendrogram
from scipy.spatial.distance import pdist, squareform


def preprocess():
    expressionList = pd.read_csv('test/input/expressionList', sep=' ')

    expressionList.index = expressionList['gene_id']
    expressionList = expressionList.drop(['gene_id'], axis=1)

    # Prepare and clean data
    # Remove rows with less than 1 TPM
    expressionList = expressionList.loc[(expressionList > 1).any(axis=1), :]

    # Check that all genes and samples have sufficiently low numbers of missing values.
    goodGenes, goodSamples, allOK = WGCNA.goodSamplesGenes(expressionList, verbose=3)
    # if not okay
    if not allOK:
        # Optionally, print the gene and sample names that were removed:
        if np.count_nonzero(goodGenes) > 0:
            print(("Removing genes:", expressionList.index[not goodGenes].values, "\n"), flush=True)
        if np.count_nonzero(goodSamples) > 0:
            print(("Removing samples:", expressionList.columns[not goodSamples].values, "\n"), flush=True)
        # Remove the offending genes and samples from the data:
        expressionList = expressionList.loc[goodGenes, goodSamples]

    print("\n\n")

    # Clustering
    sampleTree = WGCNA.hclust(pdist(expressionList.T), method="average")

    cut = 200000
    dendrogram(sampleTree, color_threshold=cut, labels=expressionList.T.index, leaf_rotation=90, leaf_font_size=8)
    plt.axhline(y=cut, c='grey', lw=1, linestyle='dashed')
    plt.title('Sample clustering to detect outliers')
    plt.xlabel('Samples')
    plt.ylabel('Distances')
    plt.tight_layout()
    plt.savefig('test/output/plots/sampleClusteringCleaning.png')

    # Determine cluster under the line
    clust = WGCNA.cutree(sampleTree, cutHeight=cut)
    # clust 0 contains the samples we want to keep.
    clust = clust.T.tolist()[0]
    index = [index for index, element in enumerate(clust) if element == 0]

    datExpr = expressionList.iloc[:, index]

    # convert trancript ID to gene ID
    for i in range(datExpr.shape[0]):
        datExpr.index.values[i] = datExpr.index[i].split(".")[0]

    datExpr = datExpr.transpose()

    datExpr.to_csv('test/output/data/data_input')


def run_WGCNA():
    datExpr = pd.read_csv('test/output/data/data_input', header=0, index_col=0)
    # Choose a set of soft-thresholding powers
    powers = list(range(1, 11)) + list(range(11, 21, 2))

    # Call the network topology analysis function
    softPower, sft = WGCNA.pickSoftThreshold(datExpr, powerVector=powers, networkType="signed hybrid")

    fig, ax = plt.subplots(ncols=2, figsize=(10, 5))

    ax[0].plot(sft['Power'], -1 * np.sign(sft['slope']) * sft['SFT.R.sq'], 'o')
    for i in range(len(powers)):
        ax[0].text(sft.loc[i, 'Power'], -1 * np.sign(sft.loc[i, 'slope']) * sft.loc[i, 'SFT.R.sq'],
                   str(sft.loc[i, 'Power']), ha="center", va="center", color='black', weight='bold')
    ax[0].axhline(0.9, color='r')
    ax[0].set_xlabel("Soft Threshold (power)")
    ax[0].set_ylabel("Scale Free Topology Model Fit,signed R^2")
    ax[0].title.set_text('Scale independence')

    ax[1].plot(sft['Power'], sft['mean(k)'], 'o')
    for i in range(len(powers)):
        ax[1].text(sft.loc[i, 'Power'], sft.loc[i, 'mean(k)'],
                   str(sft.loc[i, 'Power']), ha="center", va="center", color='r', weight='bold')
    ax[1].set_xlabel("Soft Threshold (power)")
    ax[1].set_ylabel("Mean Connectivity")
    ax[1].title.set_text('Mean connectivity')

    fig.tight_layout()
    fig.savefig('test/output/plots/summarypower.png')

    # Set Power
    adjacency = WGCNA.adjacency(datExpr, power=softPower, adjacencyType="signed hybrid")
    pd.DataFrame(adjacency).to_csv('test/output/data/adjacency')

    # Turn adjacency into topological overlap
    TOM = WGCNA.TOMsimilarity(adjacency, TOMType="signed")
    dissTOM = 1 - TOM
    dissTOM = dissTOM.round(decimals=8)
    pd.DataFrame(TOM).to_csv('test/output/data/TOM')

    # Call the hierarchical clustering function
    geneTree = WGCNA.hclust(pdist(dissTOM), method="average")
    pd.DataFrame(geneTree).to_csv('test/output/data/geneTree')

    # Plot the resulting clustering tree (dendrogram)
    plt.figure(figsize=(15, 5))
    dendrogram(geneTree, color_threshold=None, no_labels=True, leaf_rotation=90)
    plt.title('Gene clustering on TOM-based dissimilarity')
    plt.xlabel('')
    plt.ylabel('')
    plt.tight_layout()
    plt.savefig('test/output/plots/dendrogram.png')

    # We like large modules, so we set the minimum module size relatively high:
    minModuleSize = 50
    # Module identification using dynamic tree cut:
    dynamicMods = WGCNA.cutreeHybrid(dendro=geneTree, distM=dissTOM, deepSplit=2, pamRespectsDendro=False,
                                     minClusterSize=minModuleSize)

    # Convert numeric lables into colors
    dynamicColors = WGCNA.labels2colors(labels=dynamicMods)


def run_WGCNA1():
    datExpr = pd.read_csv('test/output/data/data_input', header=0, index_col=0)
    #print(datExpr)

    dynamicColors = pd.read_csv('test/input/dynamicColors', header=0).T.values[0]
    #print(dynamicColors)
    #print(len(dynamicColors))

    MEList = WGCNA.moduleEigengenes(expr=datExpr, colors=dynamicColors)

    print(MEList)
    print(len(MEList))

    # Plot the dendrogram and colors underneath
    # pdf(file="../DynamicTreeCut.pdf", width=18, height=6);
    # plotDendroAndColors(geneTree, dynamicColors, "Dynamic Tree Cut",
    #                     dendroLabels=FALSE, hang=0.03,
    #                     addGuide=TRUE, guideHang=0.05,
    #                     main="Gene dendrogram and module colors")
    # dev.off();


if __name__ == '__main__':
    # preprocess()

    # run_WGCNA()

    run_WGCNA1()
