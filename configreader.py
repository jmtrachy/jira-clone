class PropertyReader():

    props = {}

    def __init__(self, file_name):
        f = open(file_name, 'r')

        for line in f:
            line_trimmed = line.strip()
            if len(line_trimmed) > 0:
                key_value = line_trimmed.split('=')
                if len(key_value) > 1:
                    self.props[key_value[0].strip()] = key_value[1].strip()
        f.close()

    def get_property(self, key):
        return self.props[key]
