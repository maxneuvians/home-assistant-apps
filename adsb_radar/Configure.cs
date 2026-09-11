// Generate first-run configuration using the exact VRS release's settings types.
using System;
using System.IO;
using System.Xml.Serialization;
using VirtualRadar.Interface.Settings;

class Configure
{
    static void Main(string[] args)
    {
        if (File.Exists(args[0])) return;
        VirtualRadar.Library.Implementations.Register(InterfaceFactory.Factory.Singleton);
        var config = new Configuration();
        config.Receivers.Add(new Receiver {
            UniqueId = 1, Name = "RTL-SDR (dump1090)", Enabled = true,
            DataSource = DataSource.Beast, ConnectionType = ConnectionType.TCP,
            Address = "127.0.0.1", Port = 30005
        });
        config.GoogleMapSettings.WebSiteReceiverId = 1;
        config.GoogleMapSettings.ClosestAircraftReceiverId = 1;
        config.GoogleMapSettings.MapProvider = MapProvider.Leaflet;
        using (var writer = new StreamWriter(args[0]))
            new XmlSerializer(typeof(Configuration)).Serialize(writer, config);
    }
}
