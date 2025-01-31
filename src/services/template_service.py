class TemplateService:
    def create_template(self, name: str, content: str, variables: List[str]):
        template = {
            'id': generate_uuid(),
            'name': name,
            'content': content,
            'variables': variables,
            'version': 1
        }
        return self.template_repository.save(template)
    
    def render_template(self, template_id: str, data: Dict):
        template = self.template_repository.get(template_id)
        return self.renderer.render(template, data)
