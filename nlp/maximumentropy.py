from math import exp, log

from countermap import CounterMap
#from counter import Counter
from nlp import counter as Counter
from function import Function
from minimizer import Minimizer
from itertools import izip, chain, repeat

class MaxEntWeightFunction(Function):
	sigma = 1.0
	labels = None
	features = None

	def __init__(self, labeled_extracted_features, labels, features):
		self.labeled_extracted_features = labeled_extracted_features
		self.labels = labels
		self.features = features

	def get_log_probabilities(self, datum_features, weights):
		log_probs = Counter((label, sum((weights[label] * datum_features).itervalues())) for label in self.labels)
		log_probs.log_normalize()
		return log_probs

	def value_and_gradient(self, weights, verbose=True):
		objective = 0.0
		gradient = CounterMap()

		if verbose: print "Calculating log probabilities (of %d)..." % len(self.labeled_extracted_features)
		log_probs = list()
		for pos, (label, features) in enumerate(self.labeled_extracted_features):
			if verbose and pos % 100 == 0: print pos 
			log_probs.append(self.get_log_probabilities(features, weights))
		if verbose: print "Calculating objective..."
		objective = -sum(log_probs[index][label] for (index, (label,_)) in enumerate(self.labeled_extracted_features))

		empirical_counts = CounterMap()
		expected_counts = CounterMap()

		for (index, (datum_label, datum_features)) in enumerate(self.labeled_extracted_features):
			for (feature, cnt) in datum_features.iteritems():
				for label in self.labels:
					if datum_label == label:
						empirical_counts[label][feature] += cnt
					expected_counts[label][feature] += exp(log_probs[index][label]) * cnt

		if verbose: print "Calculated expected / empirical counts"
					
		gradient = expected_counts - empirical_counts

		if verbose: print "Applying penalty"
		
		# Apply a penalty (e.g. smooth the results)
		penalty = 0.0

		for label in self.labels:
			for feature in self.features:
				weight = weights[feature][label]
				penalty += weight**2
				gradient[label][feature] += (weight / (self.sigma**2))

		penalty /= 2 * self.sigma**2
		objective += penalty

		return (objective, gradient)

class MaximumEntropyClassifier:
	labels = None
	features = None
	weights = None

	def get_log_probabilities(self, datum_features):
		log_probs = Counter((label, sum((self.weights[label] * datum_features).itervalues())) for label in self.labels)
		log_probs.log_normalize()
		return log_probs
	
	def extract_features(self, datum):
		# for word in datum.split():
		# yield word
		last_last_char = ''
		last_char = ''
		for char in datum:
			yield char
			yield last_char+char
			yield last_last_char + last_char + char
			last_last_char = last_char
			last_char = char

	def train_with_features(self, labeled_features):
		print "Optimizing weights..."
		weight_function = MaxEntWeightFunction(labeled_features, self.labels, self.features)

		print "Building initial dictionary..."
		initial_weights = CounterMap()

		print self.labels
		
		for label in self.labels:
			for feature in self.features:
				initial_weights[label][feature] += 1.0

#		print initial_weights
				
		print "Minimizing..."
		self.weights = Minimizer.minimize_map(weight_function, initial_weights)

	def train(self, labeled_data):
		print "Building label set"
		self.labels = set(label for _,label in labeled_data)

		self.features = set()

		print "Labeling data..."
		labeled_features = []
		for (datum, label) in labeled_data:
			features = Counter()
			for feature in self.extract_features(datum):
				features[feature] += 1.0
				self.features.add(feature)
			labeled_features.append((label, features))

		self.train_with_features(labeled_features)

	def label(self, datum):
		datum_features = Counter(self.extract_features(datum))
		log_probs = Counter((label, self.weights[label] * datum_features) for label in self.labels)

		return log_probs.arg_max()

def read_delimited_data(file_name):
	delimited_file = open(file_name, "r")
	pairs = list()

	for line in delimited_file.readlines():
		pair = line.rstrip().split("\t")
		pair.reverse()
		pairs.append(pair)

	return pairs

def real_problem():
 	training_data = read_delimited_data("data/pnp-train.txt")
 	testing_data = read_delimited_data("data/pnp-test.txt")

 	classifier = MaximumEntropyClassifier()
 	classifier.train(training_data)

 	print "Correctly labeled %d of %d" % (sum(1 for (datum, label) in testing_data if classifier.label(datum) == label), len(testing_data))

def cnter(l):
	return Counter(izip(l, repeat(1.0, len(l))))

def toy_problem():
	training_data = (('cat', cnter(('fuzzy', 'claws', 'small'))),
					 ('bear', cnter(('fuzzy', 'claws', 'big'))),
					 ('cat', cnter(('claws', 'medium'))))
	test_data = (('cat', cnter(('claws', 'small'))),)

	classifier = MaximumEntropyClassifier()
	classifier.labels = set(('cat', 'bear'))
	classifier.features = set(('fuzzy', 'claws', 'small', 'medium', 'big'))
	classifier.train_with_features(training_data)

	print "Weights: %s" % classifier.weights
	log_probs = classifier.get_log_probabilities(test_data[0][1])
	print "Test (small cat with claws): %s" % log_probs
	for label in ['cat', 'bear']:
		print "P[%s | {small, claws}] = %f" % (label, exp(log_probs[label]))

if __name__ == "__main__":
 	print "*** Maximum Entropy Classifier ***"

	real_problem()
