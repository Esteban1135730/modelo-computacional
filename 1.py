def suma_impares(n):
    total = 0
    for i in range(1, n+1):
        impar = 2*i - 1
        total += impar

    return total

print(suma_impares(10))investigar que son los simbolos de sumatoria y producto