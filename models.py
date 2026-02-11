# models.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Word(db.Model):
    __tablename__ = 'words'
    id = db.Column(db.Integer, primary_key=True)
    english = db.Column(db.String(100), unique=True, nullable=False)
    chinese = db.Column(db.String(255), nullable=True)
    # 熟悉程度: 0=未学, 1=模糊, 2=已掌握
    status = db.Column(db.Integer, default=0) 

    def to_dict(self):
        return {
            'id': self.id,
            'english': self.english,
            'chinese': self.chinese,
            'status': self.status
        }