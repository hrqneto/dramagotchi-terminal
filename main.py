from dramagotchi.core import Dramagotchi
import os

def main():
    # Tenta carregar ou criar novo Dramagotchi
    if os.path.exists("data/save.json"):
        pet = Dramagotchi.load()
    else:
        nome = input("Dê um nome ao seu Dramagotchi: ")
        pet = Dramagotchi(nome)

    while pet.is_alive():
        pet.status()
        print("\nO que deseja fazer?")
        print("[1] Alimentar 🍗  [2] Brincar 🎾  [3] Dormir 🛌")
        print("[4] Ver gráfico 📊  [5] Sair ❌  [6] Conversar 💬")

        choice = input("Escolha: ").strip()

        if choice == "1":
            pet.feed()
        elif choice == "2":
            pet.play()
        elif choice == "3":
            pet.sleep()
        elif choice == "4":
            pet.show_emotion_chart()
        elif choice == "5":
            break
        elif choice == "6":
            pet.talk()
        else:
            print("Opção inválida.")

        pet.decay()
        pet.save()

    if not pet.is_alive():
        pet.show_summary()

if __name__ == "__main__":
    main()
