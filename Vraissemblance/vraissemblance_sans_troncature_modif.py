import numpy as np 
import pandas as pd 
import matplotlib.pyplot as plt
from scipy.optimize import minimize
from scipy.integrate import quad
import random
from tqdm import tqdm
from prettytable import PrettyTable

seller = pd.read_csv('Data/dataset_vraissemblance.csv')


X = ['type_libre','sexe_homme','sexe_femme','idf','etranger','une_tete','dec1','dec2','dec3']
columns = ['type_libre','sexe_homme','sexe_femme','idf','etranger','une_tete','dec1','dec2','dec3','tau_birth','tau_contract','Td','Ts','Td_clone','Ts_clone','tau_begin','tau_end']

### Quelques fonctions utiles ###
def phiD(beta_d): # beta_d est un vecteur de taille 9
    x_i = seller[X].values 
    phi = np.exp(np.dot(x_i,beta_d))
    return phi / phi.mean()

def phiS(beta_s): # beta_d est un vecteur de taille 9
    x_i = seller[X].values 
    phi = np.exp(np.dot(x_i,beta_s))
    return phi / phi.mean()

def IDD(delta,lambda_d,t_1,t_2): 
    if t_1 <= t_2:
        I = lambda_d * t_1
    else: 
        I = lambda_d * (t_2 + delta * (t_1 - t_2))
    return I 

def ID(lambda_d,t):
    I = lambda_d * t
    return I 

def IS(lambda_s,t):
    I = lambda_s * t
    return I 

def LSeller_i(lambda_d, lambda_s, phi_d, phi_s,delta, i):
    # numérateur
    numerateur_d_exp =  np.exp(-(phi_d[i] * IDD(delta,lambda_d,seller['Td'][i],seller['Ts'][i])))
    numerateur_d = lambda_d * phi_d[i] * delta * numerateur_d_exp
    numerateur_s_exp = np.exp(-(phi_s[i] * IS(lambda_s,seller['Ts'][i])))
    numerateur_s = lambda_s * phi_s[i] * numerateur_s_exp
    resultat = numerateur_d * numerateur_s
    return resultat


def LClone_i(lambda_d, lambda_s, phi_d, phi_s,delta, i):
    # numérateur
    numerateur_d_exp =  np.exp(-(phi_d[i] * IDD(delta,lambda_d,seller['Td_clone'][i],seller['Ts_clone'][i])))
    numerateur_d = lambda_d * phi_d[i] * delta * numerateur_d_exp
    numerateur_s_exp = np.exp(-(phi_s[i] * IS(lambda_s,seller['Ts_clone'][i])))
    numerateur_s = lambda_s * phi_s[i] * numerateur_s_exp
    resultat = numerateur_d * numerateur_s
    return resultat

def log_negatif(x):
    if x > 0: return np.log(x)
    elif x <= 0: return -np.log(-x)
vlog_negatif = np.vectorize(log_negatif)


# Fonction de vraissemblance
def likelihood(parameters):

    # Paramètres à trouver
    # lambda_d, lambda_s et delta des réels 
    # beta_d et beta_s des vecteurs de taille 8

    parameters = list(parameters)
    lambda_d = parameters[0]
    lambda_s = parameters[1]
    beta_d = list(parameters[2:11])
    beta_s = list(parameters[11:20])
    delta = parameters[-1]

    phi_d = phiD(beta_d)
    phi_s = phiS(beta_s)
    L_seller_sum = 0
    L_clone_sum = 0
    compteur = 0
    for i in tqdm(seller.index.to_list()): 
        Log_seller = log_negatif(LSeller_i(lambda_d, lambda_s, phi_d, phi_s,delta, i))
        Log_clone = log_negatif(LClone_i(lambda_d, lambda_s, phi_d, phi_s,delta, i))

        if Log_seller != np.inf and Log_clone != np.inf and Log_seller != - np.inf and Log_clone != - np.inf: 
            if Log_seller != np.nan and Log_clone != np.nan and Log_seller != None and Log_clone != None:
                compteur +=1
                L_seller_sum = L_seller_sum + Log_seller
                L_clone_sum = L_clone_sum + Log_clone
    liste_compteur.append(compteur)
    # Log_vraisemblance
    L_1 = np.sum(L_seller_sum)
    L_2 = np.sum(L_clone_sum)
    Likelihood = L_1 + L_2
    return -Likelihood

# Réduire l'ordre de grandeur des variables
seller['tau_birth'] = seller['tau_birth'] / seller['tau_birth'].mean()
seller['tau_contract'] = seller['tau_contract'] / seller['tau_contract'].mean()
seller['Ts'] = seller['Ts'] / seller['Ts'].mean()
seller['Td'] = seller['Td'] / seller['Td'].mean()
seller['Td_clone'] = seller['Td_clone'] / seller['Td_clone'].mean()
seller['Ts_clone'] = seller['Ts_clone'] / seller['Ts_clone'].mean()


num_repeats = 10
parameters_list = [
    "lambda_d", "lambda_s", "delta",
    *["beta_d" + str(i) for i in range(9)],
    *["beta_s" + str(i) for i in range(9)]
]

# Créer un DataFrame avec la colonne "parameters" et la colonne "valeurs"
data = {"parameters": parameters_list, "valeurs": [0] * len(parameters_list)}
all_estimations = []
liste_compteur = []
liste_compteur_true = []
# Répéter le calcul de la minimisation
for _ in tqdm(range(num_repeats)):
    initial_params = np.random.uniform(-50, 50, size=21)
    result = minimize(likelihood, initial_params, method='L-BFGS-B', options={'maxiter': 1000, 'disp': True, 'ftol': 1e-1})
    
    # Résultats de l'itération actuelle
    estimated_params = result.x
    success = result.success
    message = result.message
    if liste_compteur[-1] > 900:
        liste_compteur_true.append(liste_compteur[-1])
        all_estimations.append(estimated_params)
    # Ajouter les résultats de l'itération actuelle au dictionnaire
    for i, param in enumerate(estimated_params):
            if i<=20:
                data["valeurs"][i] += param
            else:
                pass

all_estimations = np.array(all_estimations)
param_means = np.mean(all_estimations, axis=0)
param_stds = np.std(all_estimations, axis=0)
result = pd.DataFrame(data)
result['valeurs'] /= len(all_estimations)
result['std'] = param_stds
print(result)
print(liste_compteur_true)