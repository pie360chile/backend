from app.backend.db.models import RolModel

class RolClass:
    def __init__(self, db):
        self.db = db

    def get_all(self):
        try:
            data = self.db.query(RolModel).order_by(RolModel.id).all()
            if not data:
                return "No data found"
            return data
        except Exception as e:
            error_message = str(e)
            return f"Error: {error_message}"
    
    def get(self, field, value):
        try:
            data = self.db.query(RolModel).filter(getattr(RolModel, field) == value).first()
            return data
        except Exception as e:
            error_message = str(e)
            return f"Error: {error_message}"
    
    def store(self, Rol_inputs):
        try:
            data = RolModel(**Rol_inputs)
            self.db.add(data)
            self.db.commit()
            return 1
        except Exception as e:
            error_message = str(e)
            return f"Error: {error_message}"
        
    def delete(self, id):
        try:
            data = self.db.query(RolModel).filter(RolModel.id == id).first()
            if data:
                self.db.delete(data)
                self.db.commit()
                return 1
            else:
                return "No data found"
        except Exception as e:
            error_message = str(e)
            return f"Error: {error_message}"
        
    def update(self, id, rol):
        existing_rol = self.db.query(RolModel).filter(RolModel.id == id).one_or_none()

        if not existing_rol:
            return "No data found"

        existing_rol_data = rol.dict(exclude_unset=True)
        for key, value in existing_rol_data.items():
            setattr(existing_rol, key, value)

        self.db.commit()

        return 1