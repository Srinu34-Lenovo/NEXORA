from app.database import init_db
from app.memory import memory_manager
from app.agent import agent
from app.tools import (
    create_task,
    list_tasks,
    complete_task
)


def print_header():

    print("\n" + "=" * 55)
    print("                    NEXORA")
    print("           Personal Intelligence OS")
    print("=" * 55)


def add_memory():

    content = input(
        "\n🧠 Enter memory: "
    ).strip()

    if content:

        memory_manager.add(content)

    else:

        print("❌ Empty memory.")


def view_memories():

    memories = memory_manager.all()

    if not memories:

        print("\n📭 No memories.")

        return

    print("\n🧠 Memories:")

    for memory in memories:

        print(
            f"{memory['id']}. "
            f"{memory['content']}"
        )


def search_memory():

    query = input(
        "\n🔎 Search: "
    ).strip()

    results = memory_manager.search_keyword(
        query
    )

    if not results:

        print("❌ No results.")

        return

    for result in results:

        print(
            f"{result['id']}. "
            f"{result['content']}"
        )


def chat():

    message = input(
        "\n🤖 You: "
    ).strip()

    if message:

        print(
            "\n🤖 NEXORA:",
            agent.chat(message)
        )


def tasks():

    print("\nTasks:")

    for task in list_tasks():

        print(
            f"{task['id']}. "
            f"{task['title']} "
            f"[{task['status']}]"
        )


def main():

    init_db()

    while True:

        print_header()

        print("1. Add Memory")
        print("2. View Memories")
        print("3. Search Memory")
        print("4. Chat with NEXORA")
        print("5. Create Task")
        print("6. View Tasks")
        print("7. Complete Task")
        print("8. Exit")

        choice = input(
            "\nChoose: "
        ).strip()

        if choice == "1":

            add_memory()

        elif choice == "2":

            view_memories()

        elif choice == "3":

            search_memory()

        elif choice == "4":

            chat()

        elif choice == "5":

            title = input(
                "Task title: "
            )

            description = input(
                "Description: "
            )

            create_task(
                title,
                description
            )

            print("✅ Task created.")

        elif choice == "6":

            tasks()

        elif choice == "7":

            tasks()

            try:

                task_id = int(
                    input(
                        "Task ID: "
                    )
                )

                if complete_task(task_id):

                    print("✅ Completed.")

                else:

                    print("❌ Task not found.")

            except ValueError:

                print("❌ Invalid ID.")

        elif choice == "8":

            print(
                "\nNEXORA shutting down. 👋"
            )

            break

        else:

            print("❌ Invalid option.")


if __name__ == "__main__":
    main()