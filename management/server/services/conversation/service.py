import mysql.connector
from database import DB_CONFIG


def get_conversations_by_user_id(user_id, page=1, size=20, sort_by="update_time", sort_order="desc"):
    """
    根据用户ID获取对话列表

    参数:
        user_id (str): 用户ID
        page (int): 当前页码
        size (int): 每页大小
        sort_by (str): 排序字段
        sort_order (str): 排序方式 (asc/desc)

    返回:
        tuple: (对话列表, 总数)
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # 直接使用user_id作为tenant_id
        tenant_id = user_id

        # 查询总记录数
        count_sql = """
        SELECT COUNT(*) as total 
        FROM dialog d
        WHERE d.tenant_id = %s
        """
        cursor.execute(count_sql, (tenant_id,))
        total = cursor.fetchone()["total"]

        # print(f"查询到总记录数: {total}")

        # 计算分页偏移量
        offset = (page - 1) * size

        # 确定排序方向
        sort_direction = "DESC" if sort_order.lower() == "desc" else "ASC"

        # 执行分页查询
        query = f"""
        SELECT 
            d.id, 
            d.name,
            d.create_date,
            d.update_date,
            d.tenant_id
        FROM 
            dialog d
        WHERE 
            d.tenant_id = %s
        ORDER BY 
            d.{sort_by} {sort_direction}
        LIMIT %s OFFSET %s
        """

        # print(f"执行查询: {query}")
        # print(f"参数: tenant_id={tenant_id}, size={size}, offset={offset}")

        cursor.execute(query, (tenant_id, size, offset))
        results = cursor.fetchall()

        print(f"查询结果数量: {len(results)}")

        # 获取每个对话的最新消息
        conversations = []
        for dialog in results:
            # 查询对话的所有消息
            conv_query = """
            SELECT id, message, name 
            FROM conversation 
            WHERE dialog_id = %s
            ORDER BY create_date DESC
            """
            cursor.execute(conv_query, (dialog["id"],))
            conv_results = cursor.fetchall()

            latest_message = ""
            conversation_name = dialog["name"]  # 默认使用dialog的name
            if conv_results and len(conv_results) > 0:
                # 获取最新的一条对话记录
                latest_conv = conv_results[0]
                # 如果conversation有name，优先使用conversation的name
                if latest_conv and latest_conv.get("name"):
                    conversation_name = latest_conv["name"]

                if latest_conv and latest_conv["message"]:
                    # 获取最后一条消息内容
                    messages = latest_conv["message"]
                    if messages and len(messages) > 0:
                        # 检查消息类型，处理字符串和字典两种情况
                        if isinstance(messages[-1], dict):
                            latest_message = messages[-1].get("content", "")
                        elif isinstance(messages[-1], str):
                            latest_message = messages[-1]
                        else:
                            latest_message = str(messages[-1])

            conversations.append(
                {
                    "id": dialog["id"],
                    "name": conversation_name,
                    "latestMessage": latest_message[:100] + "..." if len(latest_message) > 100 else latest_message,
                    "createTime": dialog["create_date"].strftime("%Y-%m-%d %H:%M:%S") if dialog["create_date"] else "",
                    "updateTime": dialog["update_date"].strftime("%Y-%m-%d %H:%M:%S") if dialog["update_date"] else "",
                }
            )

        # 关闭连接
        cursor.close()
        conn.close()

        return conversations, total

    except mysql.connector.Error as err:
        print(f"数据库错误: {err}")
        # 更详细的错误日志
        import traceback

        traceback.print_exc()
        return [], 0
    except Exception as e:
        print(f"未知错误: {e}")
        import traceback

        traceback.print_exc()
        return [], 0


def get_messages_by_conversation_id(conversation_id, page=1, size=30):
    """
    获取特定对话的详细信息

    参数:
        conversation_id (str): 对话ID
        page (int): 当前页码
        size (int): 每页大小

    返回:
        tuple: (对话详情, 总数)
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # 查询对话信息
        query = """
        SELECT *
        FROM conversation 
        WHERE dialog_id = %s
        ORDER BY create_date DESC
        """
        cursor.execute(query, (conversation_id,))
        result = cursor.fetchall()  # 确保读取所有结果

        if not result:
            print(f"未找到对话ID: {conversation_id}")
            cursor.close()
            conn.close()
            return None, 0

        # 获取第一条记录作为对话详情
        conversation = None
        if len(result) > 0:
            conversation = {
                "id": result[0]["id"],
                "dialogId": result[0].get("dialog_id", ""),
                "createTime": result[0]["create_date"].strftime("%Y-%m-%d %H:%M:%S") if result[0].get("create_date") else "",
                "updateTime": result[0]["update_date"].strftime("%Y-%m-%d %H:%M:%S") if result[0].get("update_date") else "",
                "messages": result[0].get("message", []),
            }

        # 打印调试信息
        print(f"获取到对话详情: ID={conversation_id}")
        print(f"消息长度: {len(conversation['messages']) if conversation and conversation.get('messages') else 0}")

        # 关闭连接
        cursor.close()
        conn.close()

        # 返回对话详情和消息总数
        total = len(conversation["messages"]) if conversation and conversation.get("messages") else 0
        return conversation, total

    except mysql.connector.Error as err:
        print(f"数据库错误: {err}")
        # 更详细的错误日志
        import traceback

        traceback.print_exc()
        return None, 0
    except Exception as e:
        print(f"未知错误: {e}")
        import traceback

        traceback.print_exc()
        return None, 0
