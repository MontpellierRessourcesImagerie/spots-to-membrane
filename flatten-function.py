import matplotlib.pyplot as plt
import numpy as np
from scipy.special import gamma

# Définition de l'intervalle
x = np.linspace(0.01, 1, 500)  # Start from 0.01 to avoid division by zero

# Calcul de la fonction Gamma
y = gamma(x)

# Création du plot
plt.figure(figsize=(10, 6))
plt.plot(x, y, label='Gamma Function')

plt.title('Gamma Function on Interval [0, 1]')
plt.xlabel('x')
plt.ylabel('Gamma(x)')
plt.legend()
plt.grid(True)
plt.show()
