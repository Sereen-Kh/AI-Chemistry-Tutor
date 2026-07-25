import uuid

from sqlalchemy.orm import Session

from app.models.message import Message 

class MessageRepository: 
    @staticmethod 
    def create( db: Session, message: Message 
            ) -> Message: 
               db.add(message) 
               db.commit() 
               db.refresh( message ) 
               return message 
    
    @staticmethod 
    def get_conversation_messages( db: Session, conversation_id: uuid.UUID 
            ) -> list[Message]:
            return (db.query( Message )
                            .filter( Message .conversation_id == conversation_id ) 
                            .order_by( Message .created_at .asc() ) 
                            .all() ) 
                            
    @staticmethod 
    def get_recent_messages( db: Session, conversation_id: uuid.UUID, limit: int = 12 
            ) -> list[Message]: 
                messages = (db.query(Message) 
                                .filter(Message.conversation_id == conversation_id) 
                                .order_by(Message.created_at.desc()) 
                                .limit(limit) 
                                .all()) 
                return list(reversed( messages ))