#Imports
import numpy as np 
import pandas as pd 
from scipy.optimize import minimize
from scipy.integrate import quad
from tqdm import tqdm
import random

#Charger les données
seller = pd.read_csv('Data/dataset_vraissemblance.csv')
facteur_de_normalisation = 10 ** (-4)
#Colonnes que l'on utilise
X = ['sexe_femme','idf','etranger','dec1','dec2','dec3']
columns = ['sexe_femme','idf','etranger','dec1','dec2','dec3','tau_birth','tau_contract',
           'Td','Ts','Td_clone','Ts_clone','tau_begin','tau_end']

#Fonctions pour la contribution 
def phiD(beta_d): 
    x_i = seller[X].values 
    phi = np.exp(np.dot(x_i,beta_d))
    return phi 

def phiS(beta_s): 
    x_i = seller[X].values 
    phi = np.exp(np.dot(x_i,beta_s))
    return phi 

def lambda_d(alpha_d, t):
    return np.exp(alpha_d * t)

def lambda_s(alpha_s, t):
    return t ** (alpha_s - 1)

def IDD(alpha_d, alpha_s, delta, t_1, t_2): 
    if t_1 <= t_2: I = (np.exp(alpha_d * t_1) - 1) / alpha_d
    else: I = ((1 - delta) * np.exp(alpha_d * t_2) + np.exp(alpha_d * t_1) - 1) / alpha_d
    return I 

def ID(alpha_d,t):
    return (np.exp(alpha_d * t) - 1) / alpha_d

def IS(alpha_s,t):
    return t ** alpha_s

def get_denominateur(alpha_d, alpha_s, sigma_d2,  sigma_s2, phi_d, phi_s, delta, t_end, i):
    def integrande_denominateur(t):
        gauche = 1 - (1 + sigma_d2 * phi_d[i] * IDD(alpha_d, alpha_s, delta, t_end, t)) ** (- sigma_d2 - 1)
        droite = phi_s[i] * lambda_s(alpha_s, t) * (1 + (1 + sigma_s2 * phi_s[i] * IS(alpha_s, t)) ** (- sigma_s2 - 1))
        return gauche * droite
    intervalle1 = quad(integrande_denominateur, 0, t_end)[0]
    intervalle2 = quad(integrande_denominateur, t_end, 1000)[0]
    return intervalle1 + intervalle2

#Contribution du vendeur 
def LSeller_i(alpha_d, alpha_s, sigma_d2, sigma_s2, phi_d, phi_s,delta, i):
    """
    alpha_d / alpha_s / sigma_d2/ sigma_s2/ delta des scalaires 
    phi_d / phi_s des vecteurs
    lambda_d et lambda_s des fonctions de t
    i correspond au ième vendeur  
    cette fonction retourne la contribution du ième vendeur à la fonction de vraisemblance  
    """
    #quelques variables pour faciliter la lecture
    Td = seller['Td'][i]
    Ts = seller['Ts'][i]
    t_end = (seller['tau_end'][i] - seller['tau_birth'][i]) * facteur_de_normalisation
    #numerateur
    numerateur1 = (1 + sigma_d2 * phi_d[i] * IDD(alpha_d, alpha_s, delta, Td, Ts)) ** (- sigma_d2 - 1)
    numerateur2 = delta * phi_d[i] * phi_s[i] * lambda_s(alpha_s, Ts)* lambda_d(alpha_d, Td) * (
        1 + sigma_s2 * phi_s[i] * IS(alpha_s, Ts) ** (- sigma_s2 - 1)) 
    numerateur = numerateur1 * numerateur2
    #denominateur
    denominateur = get_denominateur(alpha_d, alpha_s, sigma_d2,  sigma_s2, phi_d, phi_s, delta, t_end, i)
    #resultat
    return numerateur / denominateur

#contribution des clones 
def LClone_i(alpha_d, alpha_s, sigma_d2, sigma_s2, phi_d, phi_s,delta, i):
    """
    alpha_d / alpha_s / sigma_d2/ sigma_s2/ delta des scalaires  
    phi_d / phi_s des vecteurs
    lambda_d et lambda_s des fonctions de t
    i correspond au ième vendeur  
    cette fonction retourne la contribution du ième clone à la fonction de vraisemblance  
    """
    #quelques variables pour faciliter la lecture
    Td_seller = seller['Td'][i]
    Td_clone = seller['Td_clone'][i]
    Ts = seller['Ts'][i]
    t_end = (seller['tau_end'][i] - seller['tau_birth'][i]) * facteur_de_normalisation
    #numerateur
    numerateur1 = (1 + sigma_d2 * phi_d[i]) ** (- sigma_d2 - 1)
    numerateur2 = phi_d[i] * lambda_d(alpha_d, Td_seller) * (1 + sigma_s2 * phi_s[i] * IS(alpha_s, Td_clone)) ** (- sigma_s2 - 1)
    numerateur = numerateur1 * numerateur2
    #denominateur 
    denominateur = get_denominateur(alpha_d, alpha_s, sigma_d2,  sigma_s2, phi_d, phi_s, delta, t_end, i)
    #resultat
    return numerateur / denominateur

#fonction de vraissemblance
def likelihood(parameters):
    # Paramètres à trouver
    # lambda_d, lambda_s et delta des réels 
    # beta_d et beta_s des vecteurs de taille 6
    alpha_d = parameters[0]
    alpha_s = parameters[1]
    sigma_d2 = parameters[2]
    sigma_s2 = parameters[3]
    delta = parameters[4]
    beta_d = list(parameters[5:11])
    beta_s = list(parameters[11:17])
    phi_d = phiD(beta_d) 
    phi_s = phiS(beta_s) 
    L_seller_sum = 0
    L_clone_sum = 0
    for i in tqdm(seller.index.to_list()): 
        Log_seller_i = np.log(LSeller_i(alpha_d, alpha_s, sigma_d2, sigma_s2, phi_d, phi_s,delta, i))
        Log_clone_i = np.log(LClone_i(alpha_d, alpha_s, sigma_d2, sigma_s2, phi_d, phi_s,delta, i))
        L_seller_sum = L_seller_sum + Log_seller_i
        L_clone_sum = L_clone_sum + Log_clone_i
    Likelihood = L_seller_sum + L_clone_sum 
    return - Likelihood

# Réduire l'ordre de grandeur des variables
td_mean = (seller['Td'].mean() + seller['Td_clone'].mean()) / 2
ts_mean = seller['Ts'].mean()
seller['Ts'] = seller['Ts'] * facteur_de_normalisation
seller['Td'] = seller['Td'] * facteur_de_normalisation
seller['Td_clone'] = seller['Td_clone'] * facteur_de_normalisation
seller['Ts_clone'] = seller['Ts_clone'] * facteur_de_normalisation

#minimisation de l'opposé de la log-vraisemblance
#paramètres optimaux dans le modèle simple
initial_params = [random.uniform(-1, 0), random.uniform(-1, 0), random.uniform(1, 2), random.uniform(1, 2), 10.79241345, 
                  -0.2711224, 0.0436154, 0.04625169, 0.57186483, 0.1971254, 0.07792981, 
                  -0.38274347, 0.04600457, 0.02380623, 1.05678997,  0.45055338, 0.17921091]
alpha_d = initial_params[0]
alpha_s = initial_params[1]
sigma_d2 = initial_params[2]
sigma_s2 = initial_params[3]
delta = initial_params[4]
beta_d = list(initial_params[5:11])
beta_s = list(initial_params[11:17])
phi_d = phiD(beta_d) 
phi_s = phiS(beta_s) 


    
for i in seller.sample(10).index.to_list():
    #print(np.log(LSeller_i(alpha_d, alpha_s, sigma_d2, sigma_s2, phi_d, phi_s,delta, i)))
    t_end = (seller['tau_end'][i] - seller['tau_birth'][i]) * facteur_de_normalisation
    def get_denominateur(alpha_d, alpha_s, sigma_d2,  sigma_s2, phi_d, phi_s, delta, t_end, i):
        def integrande_denominateur(t):
            gauche = 1 - (1 + sigma_d2 * phi_d[i] * IDD(alpha_d, alpha_s, delta, t_end, t)) ** (- sigma_d2 - 1)
            droite = phi_s[i] * lambda_s(alpha_s, t) * (1 + (1 + sigma_s2 * phi_s[i] * IS(alpha_s, t)) ** (- sigma_s2 - 1))
            return gauche * droite
        intervalle1 = quad(integrande_denominateur, 0, t_end)[0]
        intervalle2 = quad(integrande_denominateur, t_end, np.inf)[0]
        print(intervalle1, intervalle2)
        return intervalle1 + intervalle2
    print(get_denominateur(alpha_d, alpha_s, sigma_d2,  sigma_s2, phi_d, phi_s, delta, t_end, i))
