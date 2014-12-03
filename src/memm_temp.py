import sys, copy, numpy
from filter import readSentences, createConditionalProbabilitiesTables, getCountsFromSentences

#TODO implement <U> smoothing

# Count the number of words in total observed
def countWords(sentences):
	count = 0
	for sentence in sentences:
		for word, tag in sentence:
			count += 1
	return count

# Break training data into buckets (per previous state)
# return buckets is a dict of lists
def divideBuckets(sentences, map_POS_index):
	buckets = {}
	previous_tag = ""
	for key in map_POS_index:
		buckets[key] = []

	for sentence in sentences:
		if not sentence:
			continue
		previous_tag = ""
		for word, tag in sentence:
			if previous_tag == "":
				buckets["<S>"].append((word, tag))
			else:
				buckets[previous_tag].append((word, tag))
			previous_tag = tag
		buckets[previous_tag].append(("<\\S>", "<\\S>"))

	return buckets

# Build the last, (o, s) specific feature
# Note tags and words are stored in all uppercase
def buildLastFeature(max_num_features, C, map_index_symbol, map_index_POS):
	last_feature_list = {}

	for i in map_index_POS:
		for j in map_index_symbol:
			word = map_index_symbol[j]
			tag = map_index_POS[i]
			total = 0
			for l in range(max_num_features):
				total += feature(l, word, tag)
			last_feature_list[(word, tag)]	= C - total

	return last_feature_list

# Indicator feature function that reutrns 1 if feature is matched otherwise 0
# This includes the n + 1 feature, which requires (word, tag) to access
# Total number of unique features = max_num_features + N * M
# WORDS ARE CASE INSENSITIVE
# f_<b, s>(O_t, S_t)
def feature(num_features, word, state, last_feature_list = {}, word_tag_tuple = ()):
	word = word.upper()

	# Done by inspection of the first file in Brown
	if num_features == 0:
		return 1 if state == "NNS" and word.endswith("S") else 0
	elif num_features == 1:
		return 1 if state == "VBD" and word.endswith("ED") else 0
	elif num_features == 2:
		return 1 if state == "VBG" and word.endswith("ING") else 0
	elif num_features == 3:
		return 1 if state == "TO" and word == "TO" else 0
	elif num_features == 4:
		return 1 if state == "DT" and word == "THE" else 0
	else:
		temp_tuple = (word, state)
		if temp_tuple == word_tag_tuple:
			return last_feature_list[(word, state)] # This should error if last_feature_list is not passed in
		else:
			print(temp_tuple)
			print(word_tag_tuple)
			assert False, "Last feature error"
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

# Initialize Lambda to 1's
def initLambda(F):
	Lambda = copy.deepcopy(F)
	for key in F:
		for inner_key in F[key]:
			Lambda[key][inner_key] = float(1)

	return Lambda

# Initialize Expectation to 0's
def initExpectation(F):
	E = copy.deepcopy(F)
	for key in F:
		for inner_key in F[key]:
			E[key][inner_key] = float(1)

	return E

# Calculate the training data average for each feature
# Length = max_num_features + N * M
def buildAverageFeature(buckets, map_POS_index, max_num_features, last_feature_list):
	F = {}

	# For each s'
	for from_tag in map_POS_index:
		bucket = buckets[from_tag]
		m_s = len(bucket)
		F[from_tag] = {}
		# Regular features + special, normalizing feature
		for l in range(max_num_features + 1):
			F[from_tag][l] = float(0)
			if m_s == 0:
				continue
			for word, tag in bucket:
				word_tag_tuple = (word, tag)
				F[from_tag][l] += feature(l, word, tag, last_feature_list, word_tag_tuple)
			F[from_tag][l] = F[from_tag][l] / m_s

		# (o, s) dependent features
		# for word_tag_tuple in last_feature_list:
		# 	print(word_tag_tuple)
		# 	F[from_tag][word_tag_tuple] = float(0)
		# 	if m_s == 0:
		# 		continue
		# 	for word, tag in bucket:
		# 		F[from_tag][word_tag_tuple] += feature(max_num_features, word, tag, last_feature_list, word_tag_tuple)
		# 	F[from_tag][word_tag_tuple] = F[from_tag][word_tag_tuple] / m_s

	return F

# Calculate the expectation for each feature
# Note this is only for 1 bucket per call
def buildExpectation(E, bucket, max_num_features, last_feature_list, TPM, map_POS_index, map_symbol_index, map_index_POS, from_tag):
	N = len(map_POS_index)
	M = len(map_symbol_index)
	m_s = len(bucket)

	i = map_POS_index[from_tag]
	for l in range(max_num_features + 1):
		E[from_tag][l] = float(0)
		if m_s == 0:
			continue
		for word, tag in bucket:
			k = map_symbol_index[word.upper()]
			for j in range(N):
				word_tag_tuple = (word, map_index_POS[j])
				# print(i, j, k, l)
				E[from_tag][l] += TPM[i*M+k][j] * feature(l, word, map_index_POS[j], last_feature_list, word_tag_tuple)
		E[from_tag][l] = E[from_tag][l] / m_s

	# for word_tag_tuple in last_feature_list:
	# 	E[from_tag][word_tag_tuple] = float(0)
	# 	if m_s == 0:
	# 		continue
	# 	previous_tag = "<S>"
	# 	for word, tag in bucket:
	# 		l = map_POS_index[previous_tag]
	# 		k = map_symbol_index[word.upper()]
	# 		for j in range(N):
	# 			E[from_tag][word_tag_tuple] += TPM[l*M+k][j] * feature(max_num_features, word, map_index_POS[j], last_feature_list, word_tag_tuple)
	# 		previous_tag = tag

	# 	E[from_tag][word_tag_tuple] = E[from_tag][word_tag_tuple] / m_s

	return E

# Use Generalized iterative scaling to learn Lambda parameter
def buildNextLambda(Lambda, C, F, E, from_tag):
	for feature_index in Lambda[from_tag]:
#		assert not(F[from_tag][feature_index] == 0 and E[from_tag][feature_index] != F[from_tag][feature_index]), "F[{0}][{1}] == 0 but not E".format(from_tag, feature_index)
		assert not(E[from_tag][feature_index] == 0 and E[from_tag][feature_index] != F[from_tag][feature_index]), "E[{0}][{1}] == 0 but not F".format(from_tag, feature_index)
		# If the average for the feature is 0 for from_tag state, it has no contribution to the probability
		if F[from_tag][feature_index] == 0:
			Lambda[from_tag][feature_index] = 0
		# if F[from_tag][feature_index] == 0 and E[from_tag][feature_index] == 0:
		# 	# Speical feature-not-found-in-observation case but still F[key] = E[key] satisfying the requirement
		# 	Lambda[from_tag][feature_index] = Lambda[from_tag][feature_index]
		else:
			log_F = numpy.log(F[from_tag][feature_index])
			log_E = numpy.log(E[from_tag][feature_index])
			# Lambda[from_tag][feature_index] = Lambda[from_tag][feature_index] + 1.0 / C * numpy.log(F[from_tag][feature_index]/E[from_tag][feature_index])
			Lambda[from_tag][feature_index] = Lambda[from_tag][feature_index] + (log_F - log_E) / C
			# print("--"*50)
			# print(F[from_tag][feature_index]),
			# print("/"),
			# print(E[from_tag][feature_index])
			# print(1.0 / C * numpy.log(F[from_tag][feature_index]/E[from_tag][feature_index]))
			# print("--"*50)

# Initialize TPM as all zeros
def initTPM(map_index_symbol, map_index_POS):
	N = len(map_index_POS)
	M = len(map_index_symbol)
	TPM = numpy.zeros(shape = (N * M, N), dtype = float)	# TPM (N * M) x N transitional probability matrix

	return 	TPM

# deprecated
# Make each row of TPM add up to 1
def normalizeTPM(TPM):
	TPM_row_sum = numpy.sum(TPM, axis = 1)

	for i in range(TPM.shape[0]):
		for j in range(TPM.shape[1]):
			TPM[i][j] = TPM[i][j] / TPM_row_sum[i]

# Create normalized transition probability matrix (TPM) given previous state and current observation
def buildTPM(TPM, Lambda, max_num_features, map_index_symbol, map_index_POS, map_POS_index, last_feature_list, from_tag):
	N = len(map_index_POS)
	M = len(map_index_symbol)

	i = map_POS_index[from_tag]
	# Calculate states
	for k in range(0, M):				# Current observation
		for j in range(0, N):			# Current/target state
			TPM[i*M+k][j] = float(0)
			word = map_index_symbol[k]
			tag = map_index_POS[j]
			word_tag_tuple = (word, tag)
			# Sum(Lambda_a * feature_a)
			for l in range(0, max_num_features + 1): # Normal features + special feature
				TPM[i*M+k][j] += Lambda[from_tag][l] * feature(l, word, tag, last_feature_list, word_tag_tuple)
			# Raise to exponential
			TPM[i*M+k][j] = numpy.exp(TPM[i*M+k][j])
		# Normalize
		row_sum = numpy.sum(TPM[i*M+k])
		for j in range(0, N):			# Current/target state
			TPM[i*M+k][j] = TPM[i*M+k][j] / row_sum

# Check if the lambdas are relatively the same
def checkLambdaConvergence(Lambda0, Lambda1, epsilon):
	for from_tag in Lambda0:
		for feature_index in Lambda0[from_tag]:
			if abs(Lambda0[from_tag][feature_index] - Lambda1[from_tag][feature_index]) > epsilon:
				return False
	return True

# Use viterbi algorithm to find the most probable sequence of tags
# Based on the hmm.py implementation
# param Pi_state_index index for tag "<S>"
# param word_sequence make sentences into single list with appended <S> and <\S>
def MEMMViterbi(TPM, Pi_state_index, word_sequence, map_symbol_index, map_POS_index):
	N = len(map_POS_index)      
	M = len(map_symbol_index)
	m = len(word_sequence)
	assert m != 0
	# Delta[s, t], Psi[s, t]
	Delta = numpy.zeros([N, m], float)		# Track Max probabilities for each t
	Psi =  numpy.zeros([N, m], int) 		# Track Maximal States for each t

	# Given the starting state (t = -1), calculate max prob. each state to current observation
	# Note that because MEMM takes both state and obs as given, only consider for each state with fix obs
	for j in range(N):
		# Initial last tag is assumed to be Pi_state_index
		word_index = map_symbol_index[word_sequence[0].upper()]
		Delta[j, 0] = TPM[Pi_state_index*M+word_index][j]
        
	# Inductive Step:
	for t in range(1, m):
		word_index = map_symbol_index[word_sequence[t].upper()]
		for j in range(N):			# For each destination state at t
			temp = numpy.zeros(N, float)
			for i in range(N):		# For each source state i at t - 1 to current state j
				temp[i] = Delta[i, t-1] * TPM[i*M+word_index][j] # 1 x N vector that stores 
			Delta[j, t] = temp.max()
			Psi[j, t] = temp.argmax()

	# Calculate State Sequence, Q*, Q* contains a sequence of j's
	# Q_star = [numpy.argmax(Delta[ :,m-1])] 
	# # Force the last element to be '<\\S>'
	# # Q_star = [map_POS_index["<\\S>"]]
	# for t in reversed(range(m-1)) :
	# 	Q_star.insert(0, Psi[Q_star[0],t+1])

	Q_star = [numpy.argmax(Delta[ :,m-1])] 
	# Force the last element to be '<\\S>'
	# Q_star = [map_POS_index["<\\S>"]]
	for t in reversed(range(m-1)) :
		Q_star.insert(0, Psi[Q_star[0],t+1])

	return (Q_star, Delta, Psi)

# # test section
numpy.set_printoptions(threshold=sys.maxint)

# sentences = readSentences("/Volumes/Storage/git/graphical_models_memm_vs_hmm/data_temp3", 1)
sentences = readSentences("/Volumes/Storage/git/graphical_models_memm_vs_hmm/data/pos/brown/", 1000)
# sentences = readSentences("/Volumes/Storage/git/graphical_models_memm_vs_hmm/data_temp2", 10)
# sentences = readSentences("/Volumes/Storage/git/graphical_models_memm_vs_hmm/data_temp/", 1)
#sentences2 = readSentences("/Volumes/Storage/git/graphical_models_memm_vs_hmm/data_bak/pos/brown/ca/", 10)

symbolsSeen, POS_tagsSeen, map_wordPOS_count, map_POSPOS_count, map_POS_count, map_word_count = getCountsFromSentences(sentences)
map_symbol_index, map_POS_index, transition_probabilities, emission_probabilities = createConditionalProbabilitiesTables(sentences, False)

# Note that (number of unique words) M <= m (number of words)
N = len(POS_tagsSeen)
M = len(symbolsSeen)
map_index_symbol =  {v: k for k, v in map_symbol_index.items()}
map_index_POS =  {v: k for k, v in map_POS_index.items()}

iter_count = 0
epsilon = 0.01 		# This is convergence threshold for Lambda
C = 6 						# This should be number of features + 1
max_num_features = C - 1
Lambda = {}
TPM = initTPM(map_index_symbol, map_index_POS)

# Divide (o,s) into |S| buckets
buckets = divideBuckets(sentences, map_POS_index)

last_feature_list =  buildLastFeature(max_num_features, C, map_index_symbol, map_index_POS)

# Initialize Lambda as 1 then learn from training data
# Lambda is different per s' (previous state)
F = buildAverageFeature(buckets, map_POS_index, max_num_features, last_feature_list)

Lambda = initLambda(F)
E = initExpectation(F)

# GIS, run until convergence
while True:
	Lambda0 = copy.deepcopy(Lambda)
	for tag in map_POS_index:
		buildTPM(TPM, Lambda, max_num_features, map_index_symbol, map_index_POS, map_POS_index, last_feature_list, tag)
	for tag in map_POS_index:
		buildExpectation(E, buckets[tag], max_num_features, last_feature_list, TPM, map_POS_index, map_symbol_index, map_index_POS, tag)
	for tag in map_POS_index:
		buildNextLambda(Lambda, C, F, E, tag)
	iter_count += 1

	if checkLambdaConvergence(Lambda0, Lambda, epsilon):
		print " ".join(["iter_count:", str(iter_count)])
		break;

numpy.save("TPM_current", TPM)
numpy.save("Lambda_current", Lambda)

print("training done")


#TEST for MATT
# i = map_POS_index["<S>"] # I
# k = map_symbol_index["MATT"]
# TPM[i*M+k][map_POS_index["N"]] = 0.9
# TPM[i*M+k][map_POS_index["V"]] = 0.1
# k = map_symbol_index["SAW"]
# TPM[i*M+k][map_POS_index["N"]] = 0.2
# TPM[i*M+k][map_POS_index["V"]] = 0.8
# k = map_symbol_index["THE"]
# TPM[i*M+k][map_POS_index["D"]] = 1
# k = map_symbol_index["CAT"]
# TPM[i*M+k][map_POS_index["N"]] = 0.9
# TPM[i*M+k][map_POS_index["V"]] = 0.1
# k = map_symbol_index["<S>"]
# TPM[i*M+k][map_POS_index["N"]] = 1
# k = map_symbol_index["<\\S>"]
# TPM[i*M+k][map_POS_index["N"]] = 1


# i = map_POS_index["N"] 
# k = map_symbol_index["MATT"]
# TPM[i*M+k][map_POS_index["N"]] = 0.9
# TPM[i*M+k][map_POS_index["V"]] = 0.1
# k = map_symbol_index["SAW"]
# TPM[i*M+k][map_POS_index["N"]] = 0.2
# TPM[i*M+k][map_POS_index["V"]] = 0.8
# k = map_symbol_index["THE"]
# TPM[i*M+k][map_POS_index["D"]] = 1
# k = map_symbol_index["CAT"]
# TPM[i*M+k][map_POS_index["N"]] = 0.9
# TPM[i*M+k][map_POS_index["V"]] = 0.1
# k = map_symbol_index["<S>"]
# TPM[i*M+k][map_POS_index["N"]] = 1
# k = map_symbol_index["<\\S>"]
# TPM[i*M+k][map_POS_index["N"]] = 1


# i = map_POS_index["V"] 
# k = map_symbol_index["MATT"]
# TPM[i*M+k][map_POS_index["N"]] = 0.8
# TPM[i*M+k][map_POS_index["V"]] = 0.2
# k = map_symbol_index["SAW"]
# TPM[i*M+k][map_POS_index["N"]] = 0.7
# TPM[i*M+k][map_POS_index["V"]] = 0.3
# k = map_symbol_index["THE"]
# TPM[i*M+k][map_POS_index["D"]] = 1
# k = map_symbol_index["CAT"]
# TPM[i*M+k][map_POS_index["N"]] = 0.95
# TPM[i*M+k][map_POS_index["V"]] = 0.05
# k = map_symbol_index["<S>"]
# TPM[i*M+k][map_POS_index["N"]] = 1
# k = map_symbol_index["<\\S>"]
# TPM[i*M+k][map_POS_index["N"]] = 1


# i = map_POS_index["D"]
# k = map_symbol_index["MATT"]
# TPM[i*M+k][map_POS_index["N"]] = 0.9
# TPM[i*M+k][map_POS_index["V"]] = 0.1
# k = map_symbol_index["SAW"]
# TPM[i*M+k][map_POS_index["N"]] = 1
# k = map_symbol_index["THE"]
# TPM[i*M+k][map_POS_index["D"]] = 1
# k = map_symbol_index["CAT"]
# TPM[i*M+k][map_POS_index["N"]] = 1
# k = map_symbol_index["<S>"]
# TPM[i*M+k][map_POS_index["N"]] = 1
# k = map_symbol_index["<\\S>"]
# TPM[i*M+k][map_POS_index["N"]] = 1


# i = map_POS_index["<\\S>"] # end state shouldn't matter
# k = map_symbol_index["MATT"]
# TPM[i*M+k][map_POS_index["N"]] = 0.9
# TPM[i*M+k][map_POS_index["V"]] = 0.1
# k = map_symbol_index["SAW"]
# TPM[i*M+k][map_POS_index["N"]] = 0.2
# TPM[i*M+k][map_POS_index["V"]] = 0.8
# k = map_symbol_index["THE"]
# TPM[i*M+k][map_POS_index["D"]] = 1
# k = map_symbol_index["CAT"]
# TPM[i*M+k][map_POS_index["N"]] = 0.9
# TPM[i*M+k][map_POS_index["V"]] = 0.1
# k = map_symbol_index["<S>"]
# TPM[i*M+k][map_POS_index["N"]] = 1
# k = map_symbol_index["<\\S>"]
# TPM[i*M+k][map_POS_index["N"]] = 1

# print(numpy.sum(TPM, axis=1))
# print(TPM)
#ENDTEST for MATT

numpy.set_printoptions(threshold=sys.maxint)

sentences = readSentences("/Volumes/Storage/git/graphical_models_memm_vs_hmm/data/pos/brown", 100)

# TPM = numpy.load("tpm_100_sen.npy")
# Lambda = numpy.load("Lambda_100_sen.npy")

symbolsSeen, POS_tagsSeen, map_wordPOS_count, map_POSPOS_count, map_POS_count, map_word_count = getCountsFromSentences(sentences)
map_symbol_index, map_POS_index, transition_probabilities, emission_probabilities = createConditionalProbabilitiesTables(sentences, False)
map_index_symbol =  {v: k for k, v in map_symbol_index.items()}
map_index_POS =  {v: k for k, v in map_POS_index.items()}

Pi_state_index = map_POS_index["<S>"]
viterbi_tuple = []
num_sentence = 0
num_sentence_correct = 0
num_tags_correct = 0
num_tags = 0 

for sentence in sentences:
	word_sequence = []
	pos_sequence = []

	# word_sequence.append('<S>')
	# pos_sequence.append('<S>')
	for word, tag in sentence:
		word_sequence.append(word)
		pos_sequence.append(tag)
	# word_sequence.append('<\S>')
	# pos_sequence.append('<\S>')

	m = len(word_sequence)
	if m == 0:
		continue

	viterbi_tuple = MEMMViterbi(TPM, Pi_state_index, word_sequence, map_symbol_index, map_POS_index)
	viterbi_sequence = [map_index_POS[x] for x in viterbi_tuple[0]]

	print("sentence {0}".format(num_sentence))
	print(word_sequence)
	print("*"*80)
	print(viterbi_sequence)
	print("*"*80)
	print(pos_sequence)
	print("*"*80)

	if viterbi_sequence == pos_sequence:
		num_sentence_correct += 1
	num_sentence += 1

	for x, y in zip(pos_sequence, viterbi_sequence):
		if x == y:
			num_tags_correct += 1
		num_tags += 1

print num_sentence_correct/float(num_sentence)
print num_tags_correct/float(num_tags)
