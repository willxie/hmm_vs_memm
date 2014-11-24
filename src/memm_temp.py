
import sys
import numpy
from filter import readSentences, createConditionalProbabilitiesTables, getCountsFromSentences

#TODO add C into functions

# Count the number of words in total observed
def countWords(sentences):
	count = 0
	for sentence in sentences:
		for word, tag in sentence:
			count += 1
	return count

# Build the last, (o, s) specific feature
def buildLastFeature(sentences, max_num_features, C):
	last_feature_list = {}

	for sentence in sentences:
		for word, tag in sentence:	# For each word tag pair
			if last_feature_list.get((word, tag), True): # Calculate if doesn't exist already
				total = 0
				for i in range(max_num_features):
					total += feature(i, word, tag)
				last_feature_list[(word, tag)]	= C - total

	return last_feature_list

# Indicator feature function that reutrns 1 if feature is matched otherwise 0
# f_<b, s>(O_t, S_t)
def feature(num_features, word, state, last_feature_list = {}, word_tag_tuple = ()):
	# Done by inspection of the first file in Brown
	if num_features == 0:
		return 1 if state == "NNS" and word.endswith("s") else 0
	elif num_features == 1:
		return 1 if state == "VBD" and word.endswith("ed") else 0
	elif num_features == 2:
		return 1 if state == "VBG" and word.endswith("ing") else 0
	elif num_features == 3:
		return 1 if state == "NNP" and word[0].isupper() else 0
	elif num_features == 4:
		return 1 if state == "DT" and word.lower() == "the" else 0
	else:
		temp_tuple = (word, state)
		if temp_tuple == word_tag_tuple:
			return last_feature_list[(word, state)] # This should error if last_feature_list is not passed in
		else:
			return 0
	'''
	featureList =
	# Nouns
	featureIndicator["NNS"] = {
		0: word.endswith("s")
	}
	# Verbs
	featureIndicator["VBG"] = {
		0: word.endswith("ing"),
		1: word.endswith("ed")
	}
	featureIndicator["VBN"] = {
		0: word.endswith("ing"),
		1: word.endswith("ed")
	}
	featureIndicator["NNP"] = {
		0: word.endswith("ing"),
		1: word.endswith("ed"),
		2: word == "JURY"
	}
	'''
	'''
	# Nouns
	if state == "NNP":
		print(word)
		print(featureNum)
		print(1 if featureIndicator.get(state, {}).get(featureNum, True) else 0)
	'''
#	if featureIndicator.get(state, {}).get(featureNum, False):
#		print("Feature found!")
    # Feature not found returns True and 1
#	return 1 if featureIndicator.get(state, {}).get(featureNum, True) else 0

# Calculate the training data average for each feature
# There are (max_num_features + len(last_feature_list) features
def buildAverageFeature(sentences, m, max_num_features, last_feature_list):
	F = {}

	for i in range(max_num_features):
		F[i] = 0.0
		for sentence in sentences:
			for word, tag in sentence:
				F[i] += feature(i, word, tag)
		F[i] = F[i] / m

	for word_tag_tuple in last_feature_list:
		F[word_tag_tuple] = 0.0
		for sentence in sentences:
			for word, tag in sentence:
				F[word_tag_tuple] += feature(max_num_features, word, tag, last_feature_list, word_tag_tuple)
		F[word_tag_tuple] = F[word_tag_tuple] / m

	return F


# Calculate the expectation for each feature
def buildExpectation(sentences, m, max_num_features, last_feature_list, TPM, map_POS_index, map_symbol_index, map_index_POS):
	E = {}
	
	for i in range(max_num_features):
		E[i] = 0.0
        previous_tag = ""
	for sentence in sentences:
		for word, tag in sentence:
			if previous_tag == "":
                		# TODO initial condition?
				E[i] += feature(i, word, tag)
			else:
				l = map_POS_index[previous_tag]
				k = map_symbol_index[word]
				for j in range(N):
					E[i] += TPM[l*M+k][j] * feature(i, word, map_index_POS[j])
				previous_tag = tag
		E[i] = E[i] / m
		
	for word_tag_tuple in last_feature_list:
		E[word_tag_tuple] = 0.0
        	previous_tag = ""
		for sentence in sentences:
			for word, tag in sentence:
				# TODO initial condition?
				if previous_tag == "":
					E[word_tag_tuple] += feature(max_num_features, word, tag, last_feature_list, word_tag_tuple)
				else:
					l = map_POS_index[previous_tag]
					k = map_symbol_index[word]
					for j in range(N):
						E[word_tag_tuple] += TPM[l*M+k][j] * feature(max_num_features, word, map_index_POS[j], last_feature_list, word_tag_tuple)
				previous_tag = tag

		E[word_tag_tuple] = E[word_tag_tuple] / m

	return E

# Use Generalized iterative scaling to learn Lambda
# param TPM (N * M) x N transitional probability matrix, normalized
# param Lambda N x C paramter matrix for the transitional probability matrix to be learned
# param F (N * M) x C feature average matrix. One value per feature pair (s, o)
# param sentences List of sentences from filter. Starts from sentences[1], each sentence contain ('word', 'tag') pair
def GIS(Lambda, C, F, E):
	for key in Lambda:
		Lambda[key] = Lambda[key] + 1 / C * numpy.log(F[key]/E[key])

		
		
# Calculate F N x C feature average matrix.
# param sentences List of sentences from filter.py
'''
def buildAverageFeatureMatrix(N, m, C, sentences):
	F = numpy.zeros(shape = (N, C))

	# Foreach feature
	for i in range(0, N):					# State
		for j in range(0, C):				# Feature number
			for sentence in sentences:		# Sum all feature values
				for word, tag in sentence:
					print(word),
					print(tag)
					F[i][j] += feature(word, tag, j)
	# Normalize
	F = F / m
	return F
'''
# Create un-normalized transition probability matrix (TPM) given previous state and current observation
# param Lambda N x C paramter matrix for the transitional probability matrix to be learned
# param V 1 x M vector of observations (words)
# param M length of V
# param C length
# param state_symbol_map 1 x N vector that stores all states
def buildTPM(N, M, Lambda, max_num_features, map_index_symbol, map_index_POS, last_feature_list):
	# TPM (N * M) x N transitional probability matrix
	TPM = numpy.zeros(shape = (N * M, N), dtype = float)

	# Calculate states
	for i in range(0, N):					# Previous state
		for k in range(0, M):				# Current observation
			for j in range(0, N):			# Current/target state
				# Sum(Lambda_a * feature_a)
				for l in range(0, max_num_features): # Normal features
#					print(i, j, k, l)
					TPM[i*M+k][j] += Lambda[l] * feature(l, map_index_symbol[k], map_index_POS[j])
				# Special feature
				word_tag_tuple = (map_index_symbol[k], map_index_POS[j])
				# TODO Could be wrong, maybe special feature should be computed through the matrix instead of observation
				if word_tag_tuple in Lambda:
					TPM[i*M+k][j] += Lambda[word_tag_tuple] * feature(max_num_features, map_index_symbol[k], map_index_POS[j], last_feature_list, word_tag_tuple)
	print(TPM)
	# Raise to exponential
	return numpy.exp(TPM)

# Make each row of TPM add up to 1
def normalizeTPM(TPM):
	TPM_row_sum = numpy.sum(TPM, axis = 1)

	for i in range(TPM.shape[0]):
		for j in range(TPM.shape[1]):
			TPM[i][j] = TPM[i][j] / TPM_row_sum[i]
	return TPM

# test section
numpy.set_printoptions(threshold=sys.maxint)

sentences = readSentences("/Volumes/Storage/git/graphical_models_memm_vs_hmm/data/pos/brown/", 3)
#sentences2 = readSentences("/Volumes/Storage/git/graphical_models_memm_vs_hmm/data_bak/pos/brown/ca/", 10)

symbolsSeen, POS_tagsSeen, map_wordPOS_count, map_POSPOS_count, map_POS_count, map_word_count = getCountsFromSentences(sentences)

map_symbol_index, map_POS_index, transition_probabilities, emission_probabilities = createConditionalProbabilitiesTables(sentences, False)

# Note that (number of unique words) M <= m (number of words)
N = len(POS_tagsSeen)
M = len(symbolsSeen)
map_index_symbol =  {v: k for k, v in map_symbol_index.items()}
map_index_POS =  {v: k for k, v in map_POS_index.items()}
m = countWords(sentences)
C = 6 # This should be number of features + 1
max_num_features = C - 1
Lambda = {}

last_feature_list = buildLastFeature(sentences, max_num_features, C)
F = buildAverageFeature(sentences, m, max_num_features, last_feature_list) # Consider coverting to numpy representation

Lambda = F.copy()
for key in F:
	Lambda[key] = 1

TPM = buildTPM(N, M, Lambda, max_num_features, map_index_symbol, map_index_POS, last_feature_list)
TPM = normalizeTPM(TPM)
print(TPM)
print("="*80)
E = buildExpectation(sentences, m, max_num_features, last_feature_list, TPM, map_POS_index, map_symbol_index, map_index_POS)
print(E)
print("="*80)
print(Lambda)

GIS(Lambda, C, F, E)
print("="*80)
print(Lambda)

'''
print("="*80)
print(F)
'''


'''
F = buildAverageFeatureMatrix(N, m, C, sentences)

print(sentences[0])
print(F)
print(numpy.shape(F))'''
#F = buildAverageFeatureMatrix(N, M, C, sentences)





"""
C = 3
state_symbol_map = ["NNS", "VB"]
N = len(state_symbol_map)
Lambda = numpy.ones(N * C).reshape((N, C))

V = ["dogs", "cats", "jumps", "flying", "eaten", "eaving", "shape", "shapes"]
"""
"""
print(state_symbol_map)
print(Lambda)
print(B)
"""
"""
TPM = buildTPM(Lambda, V, len(V), state_symbol_map)
TPM = normalizeTPM(TPM)
"""
